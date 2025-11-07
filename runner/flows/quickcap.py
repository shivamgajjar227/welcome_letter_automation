"""Headless runner implementation for the QuickCap submission stage."""

from __future__ import annotations

import datetime as _dt
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Mapping, Optional
from uuid import uuid4

from selenium.webdriver.remote.webdriver import WebDriver

import constants
from pages.quickcap_page import QuickcapPage

from .. import artifacts
from ..context import CredentialRef, RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from requests import RequestException

from ..auth import request_with_auth
from ..webhooks import (
    post_webhook,
    post_update_state_task_units,
    post_micro_update_task_units,
)
from monitoring import events
from taskunits.wla_npi import NpiWlaTU

logger = logging.getLogger(__name__)

TASK_UNITS_BASE_URL = "http://0.0.0.0:10022/api/task_units"


def _load_task_unit_dict(task_id: str) -> Dict[str, Dict[str, Any]]:
    if not task_id:
        return {}
    url = f"{TASK_UNITS_BASE_URL}/{task_id}"
    try:
        response = request_with_auth("GET", url, timeout=30)
        response.raise_for_status()
        task_units = response.json()
    except RequestException as exc:
        logger.warning(
            "Failed to fetch task units",
            extra={"task_id": task_id, "url": url, "error": str(exc)},
        )
        return {}
    mapping: Dict[str, Dict[str, Any]] = {}
    for unit in task_units or []:
        identifier = str(unit.get("identifier") or "").strip()
        if not identifier:
            continue
        mapping[identifier] = unit
        normalized = identifier.lstrip("0")
        if normalized and normalized not in mapping:
            mapping[normalized] = unit
    return mapping


class QuickcapValidationError(Exception):
    """Raised when a record cannot be processed due to validation issues."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _map_company(network: str, health_plan: str) -> Optional[str]:
    net_key = (network or "").strip().lower()
    plan_key = (health_plan or "").strip().lower()
    for raw_network, plans in constants.COMPANY_MAP.items():
        if raw_network.lower() != net_key:
            continue
        for raw_plan, company in plans.items():
            if raw_plan.lower() == plan_key:
                return company
    return None


def _map_category(category: str) -> Optional[str]:
    key = (category or "").strip().upper()
    for raw, mapped in constants.CATEGORY_MAP.items():
        if raw.upper() == key:
            return mapped
    return None


def _map_state(state: str) -> Optional[str]:
    value = (state or "").strip().lower()
    for raw, mapped in constants.STATE_DROPDOWN_MAP.items():
        if raw.lower() == value:
            return mapped
    return None


def _map_gender(gender: str) -> Optional[str]:
    if not gender:
        return None
    normalized = gender.strip().lower()
    gender_map = {
        "male": "M - Male",
        "m": "M - Male",
        "female": "F - Female",
        "f": "F - Female",
    }
    return gender_map.get(normalized)


def _format_effective_date(value: str) -> str:
    if not value:
        raise QuickcapValidationError("missing_effective_date")
    raw = value.strip()
    parse_attempts = [
        ("%b %d %Y", raw),
        ("%b %d", f"{raw} 2025"),
        ("%m/%d/%Y", raw),
    ]
    for fmt, candidate in parse_attempts:
        try:
            parsed = datetime.strptime(candidate, fmt)
            # fill year if missing
            if fmt == "%b %d":
                parsed = parsed.replace(year=datetime.utcnow().year)
            return parsed.strftime("%m/%d/%Y")
        except ValueError:
            continue
    raise QuickcapValidationError(f"invalid_effective_date:{value}")


def _select_primary_address(record: Mapping[str, Any]) -> Dict[str, Any]:
    addresses = list(record.get("practice_addresses") or [])
    if not addresses:
        return {}
    prioritized = next((addr for addr in addresses if addr.get("matches_effective_date")), None)
    return prioritized or addresses[0]


# def _normalize_record(raw_record: Mapping[str, Any]) -> Dict[str, Any]:
#     npi_number = str(raw_record.get("npi_number") or raw_record.get("npi") or "").strip()
#     if not npi_number:
#         raise QuickcapValidationError("missing_npi")
#
#     network = str(raw_record.get("network") or "").strip()
#     health_plan = str(raw_record.get("health_plan") or "").strip()
#     company_override = str(raw_record.get("company") or "").strip()
#     company_name = company_override or _map_company(network, health_plan)
#     if not company_name:
#         raise QuickcapValidationError("company_mapping_missing")
#
#     address = _select_primary_address(raw_record)
#     address_line1 = (
#         address.get("address_line_1")
#         or raw_record.get("address_line1")
#         or raw_record.get("address_line_1")
#     )
#     if not address_line1:
#         raise QuickcapValidationError("missing_address_line1")
#
#     address_line2 = address.get("address_line_2") or raw_record.get("address_line2") or ""
#     city = address.get("city") or raw_record.get("city") or ""
#     state = address.get("state") or raw_record.get("state") or ""
#     zip_code = (
#         address.get("zipcode")
#         or address.get("zip_code")
#         or raw_record.get("zip_code")
#         or raw_record.get("postal_code")
#         or ""
#     )
#     state_value = _map_state(state)
#
#     effective_date = str(raw_record.get("effective_date") or "").strip()
#     contract_date = _format_effective_date(effective_date)
#
#     group_npi = str(raw_record.get("group_npi") or "").strip()
#     if not group_npi:
#         raise QuickcapValidationError("missing_group_npi")
#
#     category = str(raw_record.get("category") or "").strip()
#     speciality = str(raw_record.get("speciality") or "").strip()
#     gender = str(raw_record.get("gender") or "").strip()
#     taxonomy_code = str(raw_record.get("taxonomy_code") or "").strip()
#     practice_name = (
#         str(raw_record.get("name") or "")
#         or str(raw_record.get("practice_name") or "")
#         or str(raw_record.get("group_name") or "")
#         or "Unknown Practice"
#     )
#
#     return {
#         "npi_number": npi_number,
#         "network": network,
#         "health_plan": health_plan,
#         "company_name": company_name,
#         "last_name": str(raw_record.get("last_name") or "").strip(),
#         "first_name": str(raw_record.get("first_name") or "").strip(),
#         "gender": _map_gender(gender),
#         "raw_gender": gender,
#         "category": category,
#         "category_option": _map_category(category),
#         "speciality": speciality,
#         "effective_date": effective_date,
#         "contract_date": contract_date,
#         "group_npi": group_npi,
#         "taxonomy_code": taxonomy_code,
#         "practice_name": practice_name,
#         "address_line1": address_line1,
#         "address_line2": address_line2,
#         "city": city,
#         "state": state,
#         "state_value": state_value,
#         "zip_code": zip_code,
#         "zip_code_clean": (address.get("zip_code_clean") or zip_code.replace("-", "")),
#     }

def safe_str(value: Any) -> str:
    """Safely convert value to string, handling None."""
    return str(value) if value is not None else ""

def _normalize_record(raw_record: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize record from database query result."""
    npi_number = str(raw_record.get("npi_number") or "")
    network = safe_str(raw_record.get("network"))
    health_plan = safe_str(raw_record.get("health_plan"))

    company_name = _map_company(network, health_plan)
    if not company_name:
        raise QuickcapValidationError("company_mapping_missing")

    effective_date = raw_record.get("effective_date")
    if isinstance(effective_date, datetime):
        effective_date = effective_date.strftime("%b %d %Y")
    elif effective_date:
        effective_date = safe_str(effective_date)

    contract_date = _format_effective_date(effective_date) if effective_date else ""

    return {
        "npi_number": npi_number,
        "network": network,
        "health_plan": health_plan,
        "company_name": company_name,
        "last_name": safe_str(raw_record.get("last_name")),
        "first_name": safe_str(raw_record.get("first_name")),
        "gender": _map_gender(safe_str(raw_record.get("gender"))),
        "category": safe_str(raw_record.get("category")),
        "category_option": _map_category(safe_str(raw_record.get("category"))),
        "speciality": safe_str(raw_record.get("speciality")),
        "effective_date": effective_date,
        "contract_date": contract_date,
        "group_npi": str(raw_record.get("group_npi") or ""),
        "taxonomy_code": safe_str(raw_record.get("taxonomy_code")),
        "practice_name": safe_str(raw_record.get("name")),
        "address_line1": safe_str(raw_record.get("address_line1")),
        "address_line2": safe_str(raw_record.get("address_line2")),
        "city": safe_str(raw_record.get("city")),
        "state": safe_str(raw_record.get("state")),
        "state_value": _map_state(safe_str(raw_record.get("state"))),
        "zip_code": str(raw_record.get("zip_code") or ""),
        "status": safe_str(raw_record.get("status")),
        "update": safe_str(raw_record.get("update")),
    }


def _build_processed_payload(data: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "npi_number": data["npi_number"],
        "company": data["company_name"],
        "status": "submitted",
        "network": data["network"],
        "health_plan": data["health_plan"],
        "group_npi": data["group_npi"],
        "taxonomy_code": data["taxonomy_code"],
        "address_updates": [
            {
                "address_line1": data["address_line1"],
                "address_line2": data["address_line2"],
                "city": data["city"],
                "state": data["state"],
                "zip_code": data["zip_code"],
                "name": data["practice_name"],
            }
        ],
        "metadata": {
            "category": data["category"],
            "speciality": data["speciality"],
            "effective_date": data["effective_date"],
        },
    }


def _get_credential(metadata: RunnerMetadata) -> CredentialRef:
    candidates = [
        metadata.credentials.get(StageName.QUICKCAP.value),
        metadata.credentials.get("quickcap"),
    ]
    for cred in candidates:
        if cred:
            return cred
    raise RuntimeError("QuickCap credentials not supplied in RunnerMetadata")


def _get_base_url(metadata: RunnerMetadata) -> str:
    candidates = [
        metadata.base_urls.get(StageName.QUICKCAP.value),
        metadata.base_urls.get("quickcap"),
        "https://pnstest.quickcap.net",
    ]
    for url in candidates:
        if url:
            return url
    raise RuntimeError("QuickCap base URL not configured")


class QuickcapProcessor:
    """Encapsulates the QuickCap UI workflow for a single provider record."""

    def __init__(self, page: QuickcapPage):
        self.page = page
        self.current_company: Optional[str] = None
        self._state_callback: Optional[
            Callable[[int, str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]], None]
        ] = None
        self._micro_callback: Optional[
            Callable[[str, Optional[Dict[str, Any]]], None]
        ] = None
        self._current_npi: Optional[str] = None

    def _set_callbacks(
        self,
        npi_value: str,
        state_callback: Optional[
            Callable[[int, str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]], None]
        ],
        micro_callback: Optional[Callable[[str, Optional[Dict[str, Any]]], None]],
    ) -> None:
        self._current_npi = npi_value
        self._state_callback = state_callback
        self._micro_callback = micro_callback

    def _clear_callbacks(self) -> None:
        self._current_npi = None
        self._state_callback = None
        self._micro_callback = None

    def _notify_state(
        self,
        state: int,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        micro_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if self._state_callback:
            self._state_callback(state, message, data, micro_extra)

    def _notify_micro(self, message: str, extra: Optional[Dict[str, Any]] = None) -> None:
        if self._micro_callback:
            self._micro_callback(message, extra)

    def process(
        self,
        raw_record: Mapping[str, Any],
        state_callback: Optional[
            Callable[[int, str, Optional[Dict[str, Any]], Optional[Dict[str, Any]]], None]
        ] = None,
        micro_callback: Optional[Callable[[str, Optional[Dict[str, Any]]], None]] = None,
    ) -> Dict[str, Any]:
        data = _normalize_record(raw_record)
        self._set_callbacks(data["npi_number"], state_callback, micro_callback)
        self._ensure_company(data["company_name"])
        self._ensure_practitioner_context()
        self._search_npi(data["npi_number"])

        try:
            self._run_quick_add_sequence(data)
            self._update_healthplan_and_taxonomy(data)
        finally:
            self._cleanup_to_main()
            self._clear_callbacks()

        return _build_processed_payload(data)

    # ------------------------------------------------------------------ helpers

    # def _ensure_company(self, company_name: str) -> None:
    #     if self.current_company and self.current_company.lower() == company_name.lower():
    #         return
    #     if not self.page.choose_company(company_name):
    #         raise QuickcapValidationError(f"company_switch_failed:{company_name}")
    #     self.current_company = company_name
    #     self.page.set_main_window_before_switching()

    def _ensure_company(self, company_name: str) -> None:
        """Switch company if needed."""
        if self.current_company and self.current_company.lower() == company_name.lower():
            self._notify_state(
                NpiWlaTU.TU_LOGGED_INTO_COMPANY,
                "Using existing QuickCap company session",
                {"company": company_name},
            )
            return


        self.page.store_main_window()
        self.page.click_change_company()
        self.page.switch_to_new_window1()
        self.page.choose_company(company_name)
        self.page.enter_username_in_company_prompt("autoprocess@pns-mgmt.com")
        self.page.enter_password_in_company_prompt("Pns@072025")
        self.page.click_login_button_in_company_prompt()
        self.page.switch_to_main()
        self.current_company = company_name
        self._notify_state(
            NpiWlaTU.TU_LOGGED_INTO_COMPANY,
            "Switched company in QuickCap",
            {"company": company_name},
        )



    def _ensure_practitioner_context(self) -> None:
        if not self.page.check_npi_search_field():
            self.page.ensure_credentialing_tab()
            self.page.choose_credentialing_tab()
        self.page.choose_practitioner_data()

    # def _search_npi(self, npi: str) -> None:
    #     if not npi:
    #         raise QuickcapValidationError("missing_npi")
    #     self.page.enter_npi(npi)
    #     self.page.click_search_button()

    def _search_npi(self, npi: str) -> None:
        """Search for NPI in QuickCap."""

        if self.page.is_access_denied():
            self.page.driver.back()

        if self.page.check_npi_search_field():
            self.page.enter_npi(npi)
            self.page.click_search_button()
        else:
            self.page.ensure_credentialing_tab()
            self.page.choose_credentialing_tab()
            self.page.choose_practitioner_data()
            self.page.enter_npi(npi)
            self.page.click_search_button()

    def _run_edit_flow(self, data: Dict[str, Any]) -> None:
        """Execute Edit flow for existing providers."""

        self.page.click_edit_button()
        self.page.switch_to_new_window1()
        self.page.click_provider_button()

        provider_id = self.page.provider_table_rows()
        self.page.click_add_provider()
        self.page.switch_to_new_window1()

        self._populate_provider_form(data, provider_id)
        self._link_organization(data)
        self._enter_provider_location(data)
        self._update_healthplan_and_taxonomy(data)
        # self._update_database

    def _populate_provider_form(self, data: Dict[str, Any], provider_id: str) -> None:
        """Populate provider form in Edit flow."""

        self.page.enter_provider_letter(provider_id)
        self.page.enter_last_name(data.get("last_name", ""))
        self.page.enter_first_name(data.get("first_name", ""))
        self.page.enter_effective_date(data["contract_date"])
        self.page.select_contract_type1("CONTRACT FEE FOR SERVICE")
        self.page.select_speciality1(data.get("network", ""))
        self.page.select_payment_type("FEE FOR SERVICE")
        self.page.enter_contract_from_date(data["contract_date"])
        self.page.select_provider_type_dropdown1(
            data.get("category", ""),
            data.get("network", ""),
            data.get("speciality", "")
        )
        self.page.select_account1("0000-000 DEFAULT")
        self.page.select_template1(data["company_name"])

    def _enter_provider_location(self, data: Dict[str, Any]) -> None:
        """Enter provider location in Edit flow."""

        self.page.switch_to_new_window1()
        self.page.click_add_new_location()
        self.page.enter_name1(data.get("practice_name", ""))
        self.page.enter_address2(data["address_line1"])
        self.page.enter_address_line2(data.get("address_line2", ""))

        if data.get("state_value"):
            self.page.select_state1(data["state_value"])

        self.page.enter_zip1(data.get("zip_code", ""))
        self.page.enter_city1(data.get("city", ""))
        self.page.click_primary()
        self.page.click_save1()

        # Close popup if exists
        if self.page.driver.current_window_handle != self.main_window:
            self.page.driver.close()
            self.page.driver.switch_to.window(self.main_window)

    def _run_quick_add_sequence(self, data: Mapping[str, Any]) -> None:
        used_quick_add = True
        try:
            self.page.click_quick_add_button()
            self.page.switch_to_new_window1()
            self._populate_quick_add_form(data)
            self._link_organization(data)
            self._enter_practice_location(data)
            self._save_contract_form()
        except Exception as exc:
            logger.debug("Quick add flow failed (%s); falling back to existing provider path", exc)
            used_quick_add = False
            self._handle_existing_provider_flow(data)
        state = (
            NpiWlaTU.TU_NEW_NPI_QUICK_ADDED
            if used_quick_add
            else NpiWlaTU.TU_ANOTHER_NPI_ADDED
        )
        self._notify_state(
            state,
            "Completed provider entry in QuickCap",
            {
                "npi": data["npi_number"],
                "company": data["company_name"],
                "flow": "quick_add" if used_quick_add else "existing_provider",
            },
        )
        self._notify_state(
            NpiWlaTU.TU_NPI_QUICK_ENTRY_DONE,
            "Completed QuickCap entry flow",
            {"npi": data["npi_number"]},
        )

    def _populate_quick_add_form(self, data: Mapping[str, Any]) -> None:
        if data.get("category_option"):
            self.page.select_category_dropdown(data["category_option"])
        self.page.select_provider_type_dropdown(
            data.get("category", ""),
            data.get("network", ""),
            data.get("speciality", ""),
        )
        self.page.select_speciality(data.get("network", ""))
        self.page.click_quick_add_window_npi_button(data["npi_number"])
        self.page.enter_provider_id(f"{data['npi_number']}(A)")
        self.page.enter_last_first_name(data.get("last_name", ""), data.get("first_name", ""))
        if data.get("gender"):
            self.page.select_gender(data["gender"])
        self.page.enter_contract_from_date(data["contract_date"])
        self.page.select_contract_type("CONTRACT FEE FOR SERVICE")
        self.page.select_payment_type("FEE FOR SERVICE")
        self.page.select_account("0000-000 DEFAULT")

    # def _link_organization(self, data: Mapping[str, Any]) -> None:
    #     self.page.click_organization()
    #     self.page.switch_to_new_window1()
    #     self.page.enter_npi_org(data["group_npi"])
    #     self.page.click_search_npi()
    #     if not self.page.click_org_id(data["npi_number"], data["address_line1"]):
    #         raise QuickcapValidationError("org_id_not_found")
    #     self.page.switch_to_previous_window()

    def _link_organization(self, data: Dict[str, Any]) -> None:
        """Link NPI to organization."""

        self.page.click_organization()
        self.page.switch_to_new_window1()
        self.page.enter_npi_org(data["group_npi"])
        self.page.click_search_npi()

        success = self.page.click_org_id(data["npi_number"], data["address_line1"])
        if not success:
            # self._update_database_status(data, success=False, error="org_id_not_found")
            raise QuickcapValidationError("org_id_not_found")

        self.page.switch_to_previous_window()

    def _enter_practice_location(self, data: Mapping[str, Any]) -> None:
        self.page.select_practice_type("GRP - GROUP")
        self.page.enter_name(data.get("practice_name", ""))
        self.page.enter_address1(data["address_line1"])
        self.page.enter_address_line_2(data.get("address_line2", ""))
        if data.get("state_value"):
            self.page.select_state(data["state_value"])
        self.page.enter_city(data.get("city", ""))
        self.page.enter_zip(data.get("zip_code", ""))
        self.page.select_contract_template(data["company_name"])

    def _save_contract_form(self) -> None:
        self.page.click_save()
        try:
            self.page.accept_alert()
            self.page.dismiss_alert()
        except Exception:
            logger.debug("No alert displayed after saving contract form")
        try:
            self.page.driver.close()
        except Exception:
            logger.debug("No popup to close after contract save")
        self.page.switch_to_new_window1()
        try:
            self.page.switch_back_to_main()
        except Exception:
            logger.debug("Main window already active after save")

    def _handle_existing_provider_flow(self, data: Mapping[str, Any]) -> None:
        self.page.click_edit_button()
        self.page.switch_to_new_window1()
        self.page.click_provider_button()
        provider_id = self.page.provider_table_rows() or "A"
        self.page.click_add_provider()
        self.page.switch_to_new_window1()
        self.page.enter_provider_letter(provider_id)
        self.page.enter_last_name(data.get("last_name", ""))
        self.page.enter_first_name(data.get("first_name", ""))
        self.page.enter_effective_date(data["contract_date"])
        self.page.select_contract_type1("CONTRACT FEE FOR SERVICE")
        self.page.select_speciality1(data.get("network", ""))
        self.page.select_payment_type("FEE FOR SERVICE")
        self.page.enter_contract_from_date(data["contract_date"])
        self.page.select_provider_type_dropdown1(
            data.get("category", ""), data.get("network", ""), data.get("speciality", "")
        )
        self.page.select_account1("0000-000 DEFAULT")
        self.page.select_template1(data["company_name"])
        self._link_organization(data)
        self.page.switch_to_new_window1()
        self.page.click_add_new_location()
        self.page.enter_name1(data.get("practice_name", ""))
        self.page.enter_address2(data["address_line1"])
        self.page.enter_address_line2(data.get("address_line2", ""))
        if data.get("state_value"):
            self.page.select_state1(data["state_value"])
        self.page.enter_zip1(data.get("zip_code", ""))
        self.page.enter_city1(data.get("city", ""))
        self.page.click_primary()
        self.page.click_save1()
        try:
            self.page.accept_alert()
            self.page.dismiss_alert()
        except Exception:
            logger.debug("No alert displayed while saving existing provider location")
        try:
            self.page.driver.close()
        except Exception:
            logger.debug("Existing provider popup already closed")
        self.page.switch_to_new_window1()
        try:
            self.page.switch_back_to_main()
        except Exception:
            logger.debug("Main window already focused after provider update")

    def _update_healthplan_and_taxonomy(self, data: Mapping[str, Any]) -> None:
        self.page.enter_npi(data["npi_number"])
        self.page.click_search_button()
        if not self.page.is_edit_button_available():
            raise QuickcapValidationError("edit_button_unavailable")

        self.page.set_main_window_before_switching()
        self.page.click_edit_button()
        self.page.switch_to_new_window()
        self.page.click_provider_button()
        provider_id = self.page.provider_table_rows() or "A"
        try:
            self.page.click_edit_for_healthplan(provider_id)
        except Exception:
            self.page.click_edit_for_healthplan_for_A()
        self.page.click_healthplan_panel()
        self.page.switch_to_new_window1()
        self.page.enter_membership_date(data["contract_date"])
        self.page.click_plus_button()
        self.page.click_save_healthplan()
        try:
            self.page.driver.close()
        except Exception:
            logger.debug("Healthplan window already closed")
        self._notify_state(
            NpiWlaTU.TU_HEALTH_PLAN_ENTRY_DONE,
            "Added health plan information in QuickCap",
            {
                "npi": data["npi_number"],
                "health_plan": data["health_plan"],
                "network": data["network"],
            },
        )

        self.page.switch_to_new_window()
        self.page.click_other_ids()
        self.page.click_add_plus()
        self.page.select_taxonomy("TAXONOMY - TAXONOMY")
        try:
            self.page.click_provider_id(provider_id)
        except Exception:
            self.page.click_provider_id_for_A()
        if data.get("taxonomy_code"):
            self.page.enter_taxonomy_code(data["taxonomy_code"])
        self.page.click_save_taxonomy()
        self._notify_state(
            NpiWlaTU.TU_OTHER_IDS_ENTRY_DONE,
            "Added taxonomy/other IDs in QuickCap",
            {"npi": data["npi_number"], "taxonomy_code": data.get("taxonomy_code")},
        )

    def _cleanup_to_main(self) -> None:
        try:
            self.page.switch_back_to_main()
        except Exception:
            try:
                self.page.driver.switch_to.window(self.page.driver.window_handles[0])
            except Exception:
                logger.debug("Unable to switch back to main window during cleanup")


def run(driver: WebDriver, metadata: RunnerMetadata) -> StageResult:
    stage_result = StageResult(stage=StageName.QUICKCAP)
    stage_run_id = uuid4().hex
    stage_started_at = _dt.datetime.now(_dt.timezone.utc)
    stage_artifact_refs: List[Dict[str, Any]] = []

    structured_log(
        logger,
        "stage_started",
        stage=StageName.QUICKCAP.value,
        task_id=metadata.task_id,
        stage_run_id=stage_run_id,
    )
    events.emit_stage_event(
        task_id=metadata.task_id,
        stage=StageName.QUICKCAP,
        event="stage_started",
        status="in_progress",
        stage_run_id=stage_run_id,
        started_at=stage_started_at.isoformat(),
    )

    task_unit_dict = _load_task_unit_dict(metadata.task_id)
    records: List[Dict[str, Any]] = list(task_unit_dict.values())

    structured_log(
        logger,
        "stage_start",
        stage=StageName.QUICKCAP.value,
        task_id=metadata.task_id,
        payload_count=len(records),
    )

    if not records:
        stage_result.data["processed"] = []
        stage_result.data["failed"] = []
        stage_result.mark_finished(success=True)
        finished_at = _dt.datetime.now(_dt.timezone.utc)
        events.emit_stage_event(
            task_id=metadata.task_id,
            stage=StageName.QUICKCAP,
            event="stage_completed",
            status="completed",
            stage_run_id=stage_run_id,
            started_at=stage_started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((finished_at - stage_started_at).total_seconds() * 1000),
            summary={"records_total": 0, "records_success": 0, "records_failed": 0},
            artifacts=stage_artifact_refs,
        )
        return stage_result

    cred = _get_credential(metadata)
    base_url = _get_base_url(metadata)

    driver.get(base_url)
    quickcap_page = QuickcapPage(driver)
    try:
        quickcap_page.click_company()
    except Exception:
        logger.debug("Company selection icon not clickable before login; continuing")

    try:
        quickcap_page.login(cred.username, cred.password)
    except Exception as exc:
        structured_log(
            logger,
            "login_failure",
            stage=StageName.QUICKCAP.value,
            task_id=metadata.task_id,
            error=str(exc),
        )
        stage_result.artifacts.append(
            artifacts.capture_screenshot(driver, metadata, StageName.QUICKCAP, "login_failure")
        )
        stage_result.mark_finished(success=False, error=str(exc))
        finished_at = _dt.datetime.now(_dt.timezone.utc)
        events.emit_stage_event(
            task_id=metadata.task_id,
            stage=StageName.QUICKCAP,
            event="stage_failed",
            status="failed",
            stage_run_id=stage_run_id,
            started_at=stage_started_at.isoformat(),
            finished_at=finished_at.isoformat(),
            duration_ms=int((finished_at - stage_started_at).total_seconds() * 1000),
            message=str(exc),
            artifacts=[],
        )
        return stage_result

    processed: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []
    processed_task_unit_ids = set()
    processor = QuickcapProcessor(quickcap_page)

    def _record_state_transition(
        task_unit: Optional[Dict[str, Any]],
        npi_value: str,
        new_state: int,
        message: str,
        data_payload: Optional[Dict[str, Any]] = None,
        micro_extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not task_unit:
            logger.debug("Task unit missing for NPI %s; skipping state update", npi_value)
            return
        update_meta = {"npi": npi_value}
        if data_payload:
            update_meta.update(data_payload)
        payload = {
            "updates": [
                {
                    "task_unit_id": task_unit["task_unit_id"],
                    "state": str(new_state),
                    "transition_reason": message,
                    "state_value": 0,
                    "meta_data": update_meta,
                }
            ]
        }
        post_update_state_task_units(payload=payload)
        task_unit["current_state"] = new_state
        update_data = {"message": message, "npi": npi_value}
        if micro_extra:
            update_data.update(micro_extra)
        elif data_payload:
            update_data.update(data_payload)
        post_micro_update_task_units(
            payload={
                "updates": [
                    {
                        "task_unit_id": task_unit["task_unit_id"],
                        "update_state": new_state,
                        "update_data": update_data,
                    }
                ]
            }
        )

    def _record_micro_update(
        task_unit: Optional[Dict[str, Any]],
        npi_value: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not task_unit:
            logger.debug("Task unit missing for NPI %s; skipping micro update", npi_value)
            return
        update_data = {"message": message, "npi": npi_value}
        if extra:
            update_data.update(extra)
        post_micro_update_task_units(
            payload={
                "updates": [
                    {
                        "task_unit_id": task_unit["task_unit_id"],
                        "update_state": task_unit.get("current_state"),
                        "update_data": update_data,
                    }
                ]
            }
        )

    def _make_state_callback(task_unit: Dict[str, Any], npi_value: str):
        def _callback(
            state: int,
            message: str,
            data_payload: Optional[Dict[str, Any]] = None,
            micro_extra: Optional[Dict[str, Any]] = None,
        ) -> None:
            _record_state_transition(task_unit, npi_value, state, message, data_payload, micro_extra)

        return _callback

    def _make_micro_callback(task_unit: Dict[str, Any], npi_value: str):
        def _callback(message: str, extra: Optional[Dict[str, Any]] = None) -> None:
            _record_micro_update(task_unit, npi_value, message, extra)

        return _callback

    for identifier, task_unit in task_unit_dict.items():
        task_unit_id = task_unit.get("task_unit_id")
        if not task_unit_id or task_unit_id in processed_task_unit_ids:
            continue
        processed_task_unit_ids.add(task_unit_id)

        npi = str(
            task_unit.get("identifier")
            or task_unit.get("npi_number")
            or identifier
            or ""
        ).strip()
        if not npi:
            failures.append(
                {
                    "reason": "missing_npi",
                    "task_unit_id": task_unit_id,
                }
            )
            _record_micro_update(
                task_unit,
                "unknown",
                "Task unit missing identifier; skipping QuickCap run",
                {"task_unit_id": task_unit_id},
            )
            continue

        record = dict(task_unit)
        record.setdefault("npi_number", npi)
        attempt = int(record.get("attempt", 1) or 1)

        events.emit_npi_event(
            task_id=metadata.task_id,
            stage=StageName.QUICKCAP,
            npi=npi,
            status="in_progress",
            attempt=attempt,
            stage_run_id=stage_run_id,
            input_snapshot=record,
        )
        artifact_start_idx = len(stage_result.artifacts)
        status = "completed"
        message: Optional[str] = None
        output_snapshot: Dict[str, Any] = {"npi_number": npi, "status": "submitted"}
        state_callback = _make_state_callback(task_unit, npi)
        micro_callback = _make_micro_callback(task_unit, npi)

        try:
            result = processor.process(
                record,
                state_callback=state_callback,
                micro_callback=micro_callback,
            )
            processed.append(result)
            screenshot = artifacts.capture_screenshot(
                driver, metadata, StageName.QUICKCAP, f"success_{npi}"
            )
            stage_result.artifacts.append(screenshot)
            structured_log(
                logger,
                "record_complete",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=npi,
            )
            artifact_refs = stage_result.artifacts[artifact_start_idx:]
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.QUICKCAP,
                npi=npi,
                status="completed",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot=record,
                output_snapshot=result,
                artifacts=artifact_refs,
            )
        except QuickcapValidationError as exc:
            status = "failed"
            message = exc.reason or str(exc)
            failure_entry = {"npi_number": npi, "error": message}
            failures.append(failure_entry)
            stage_result.artifacts.append(
                artifacts.capture_screenshot(
                    driver, metadata, StageName.QUICKCAP, f"validation_failure_{npi}"
                )
            )
            structured_log(
                logger,
                "record_validation_failure",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=npi,
                error=message,
            )
            if exc.reason == "org_id_not_found":
                _record_state_transition(
                    task_unit,
                    npi,
                    NpiWlaTU.TU_ERROR_ORG_ID_NOT_FOUND,
                    "Organization ID not found in QuickCap",
                    data_payload={"npi": npi},
                    micro_extra={"error": message},
                )
            else:
                _record_micro_update(
                    task_unit,
                    npi,
                    "Validation failure during QuickCap run",
                    {"error": message},
                )
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.QUICKCAP,
                npi=npi,
                status="failed",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot=record,
                output_snapshot=failure_entry,
                artifacts=[],
                message=message,
            )
        except Exception as exc:  # pragma: no cover
            status = "failed"
            message = str(exc)
            failure_entry = {"npi_number": npi, "error": message}
            failures.append(failure_entry)
            stage_result.artifacts.append(
                artifacts.capture_screenshot(
                    driver, metadata, StageName.QUICKCAP, f"failure_{npi}"
                )
            )
            structured_log(
                logger,
                "record_failure",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=npi,
                error=message,
            )
            _record_micro_update(
                task_unit,
                npi,
                "Exception while processing QuickCap record",
                {"error": message},
            )
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.QUICKCAP,
                npi=npi,
                status="failed",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot=record,
                output_snapshot=failure_entry,
                artifacts=[],
                message=message,
            )
        finally:
            structured_log(
                logger,
                "record_finished",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=npi,
                status=status,
            )

    payload = {
        "task_id": metadata.task_id,
        "stage": StageName.QUICKCAP.value,
        "processed": processed,
        "failed": failures,
    }
    post_webhook(metadata, StageName.QUICKCAP, payload)

    stage_result.data["processed"] = processed
    stage_result.data["failed"] = failures
    success = not failures
    stage_result.mark_finished(success=success)
    finished_at = _dt.datetime.now(_dt.timezone.utc)
    events.emit_stage_event(
        task_id=metadata.task_id,
        stage=StageName.QUICKCAP,
        event="stage_completed" if success else "stage_failed",
        status="completed" if success else "failed",
        stage_run_id=stage_run_id,
        started_at=stage_started_at.isoformat(),
        finished_at=finished_at.isoformat(),
        duration_ms=int((finished_at - stage_started_at).total_seconds() * 1000),
        summary={
            "records_total": len(records),
            "records_success": len(processed),
            "records_failed": len(failures),
        },
        message=None if success else "one_or_more_records_failed",
        artifacts=stage_artifact_refs,
    )
    structured_log(
        logger,
        "stage_finished",
        stage=StageName.QUICKCAP.value,
        task_id=metadata.task_id,
        stage_run_id=stage_run_id,
        success=success,
        failures=len(failures),
    )
    return stage_result
