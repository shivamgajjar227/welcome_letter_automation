"""Headless runner implementation for the QuickCap submission stage."""

from __future__ import annotations

import datetime as _dt
import logging
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional
from uuid import uuid4

from selenium.common import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver

import constants
from pages.quickcap_page import QuickcapPage

from .. import artifacts
from ..context import CredentialRef, RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from ..webhooks import (
    post_webhook,
    post_update_state_task_units,
    post_micro_update_task_units,
)
from ..auth import request_with_auth
from requests import RequestException
from monitoring import events
from taskunits.wla_npi import NpiWlaTU

logger = logging.getLogger(__name__)

TASK_UNITS_BASE_URL = "http://0.0.0.0:10022/api/task_units"


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


def _flatten_quickcap_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for record in records:
        addresses = record.get("practice_addresses") or []
        if not addresses:
            expanded = dict(record)
            flattened.append(expanded)
            continue
        for address in addresses:
            expanded = dict(record)
            # Bring all practice address keys to the top-level record without overwriting existing values.
            for key, value in address.items():
                expanded[key] = value
            flattened.append(expanded)
    return flattened




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

    def process(self, raw_record: Mapping[str, Any]) -> Dict[str, Any]:
        data = _normalize_record(raw_record)
        self._ensure_company(data["company_name"])
        self._ensure_practitioner_context()
        self._search_npi(data["npi_number"])

        try:
            self._run_quick_add_sequence(data)
            self._update_healthplan_and_taxonomy(data)
        finally:
            self._cleanup_to_main()

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
        try:
            self.page.click_quick_add_button()
            self.page.switch_to_new_window1()
            self._populate_quick_add_form(data)
            self._link_organization(data)
            self._enter_practice_location(data)
            self._save_contract_form()
        except Exception as exc:
            logger.debug("Quick add flow failed (%s); falling back to existing provider path", exc)
            self._handle_existing_provider_flow(data)

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

    """
    TODO Yash:
    In the beginning of any task or stage, we will initialise the relevant task unit dictionary.
    """
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
    records: List[Dict[str, Any]] = _flatten_quickcap_records(list(task_unit_dict.values()))

    structured_log(
        logger,
        "stage_start",
        stage=StageName.QUICKCAP.value,
        task_id=metadata.task_id,
        payload_count=len(records),
    )

    if not records:
        stage_result.mark_finished(success=True)
        stage_result.data["processed"] = []
        stage_result.data["failed"] = []
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

    def _task_unit_for_npi(npi_value: str) -> Optional[Dict[str, Any]]:
        normalized = str(npi_value or "").strip()
        if not normalized:
            return None
        if normalized in task_unit_dict:
            return task_unit_dict[normalized]
        alt_identifier = normalized.lstrip("0")
        if alt_identifier and alt_identifier in task_unit_dict:
            return task_unit_dict[alt_identifier]
        return None

    def _record_state_transition(
        record: Dict[str, Any],
        npi_value: str,
        new_state: int,
        message: str,
        micro_extra: Optional[Dict[str, Any]] = None,
    data_payload=None) -> None:
        task_unit = task_unit_dict[npi_value] if npi_value in task_unit_dict else None
        payload = {
            "updates": [
                {
                    "task_unit_id": task_unit["task_unit_id"],
                    "state": str(new_state),
                    "transition_reason": message,
                    "state_value": 0,
                    "meta_data": task_unit,
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
                        "update_type": micro_extra.get("update_type",0),
                        "message": message
                    }
                ]
            }
        )

    def _record_micro_update(
        record: Dict[str, Any],
        npi_value: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        state_override: Optional[int] = None,
    update_data=None) -> None:
        task_unit = task_unit_dict[npi_value] if npi_value in task_unit_dict else None
        if not task_unit:
            logger.debug("Task unit not found for NPI %s; skipping micro update", npi_value)
            return
        update_data["message"] = message
        update_data["npi"] = npi_value
        if extra:
            update_data.update(extra)
        current_address = record.get("_current_address")
        if current_address:
            update_data.setdefault("address", current_address)
        payload = {
            "updates": [
                {
                    "task_unit_id": task_unit["task_unit_id"],
                    "update_state": state_override if state_override is not None else task_unit.get("current_state"),
                    "update_data": update_data,
                    "update_type": extra.get("update_type",0),
                    "message": message
                }
            ]
        }
        post_micro_update_task_units(payload=payload)

    cred = _get_credential(metadata)
    base_url = _get_base_url(metadata)

    driver.get(base_url)
    quickcap_page = QuickcapPage(driver)
    main_window = driver.current_window_handle
    try:
        quickcap_page.click_company()
    except Exception:
        logger.debug("Company selection icon not clickable before login; continuing")

    try:
        quickcap_page.login(cred.username, cred.password)

        stage_result.artifacts.append(
            artifacts.capture_screenshot(driver, metadata, StageName.QUICKCAP, "after_login")
        )
    except Exception as exc:  # pragma: no cover
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
    current_company = None
    processed: List[Dict] = []
    failures: List[Dict] = []
    processor = QuickcapProcessor(quickcap_page)

    for record in records:
        npi = str(
            record.get("npi_number") or record.get("npi") or record.get("identifier") or ""
        ).strip()
        attempt = int(record.get("attempt", 1) or 1)
        record.setdefault("npi_number", npi)
        events.emit_npi_event(
            task_id=metadata.task_id,
            stage=StageName.QUICKCAP,
            npi=npi or "unknown",
            status="in_progress",
            attempt=attempt,
            stage_run_id=stage_run_id,
            input_snapshot=record,
        )
        if not npi:
            failures.append({"reason": "missing_npi", "record": record})
            _record_micro_update(
                record,
                "unknown",
                "Task unit missing NPI; skipping QuickCap processing",
                extra={"record": record},
            )
            continue
        status = "completed"
        message: Optional[str] = None
        output_snapshot: Dict[str, Any] = {
            "npi_number": npi or record.get("npi"),
            "status": "submitted",
        }
        artifact_start_idx = len(stage_result.artifacts)
        try:
            structured_log(
                logger,
                "record_start",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=npi or "unknown",
            )

            npi_number = str(record.get("npi_number") or "")
            network = safe_str(record.get("network"))
            health_plan = safe_str(record.get("health_plan"))
            last_name = safe_str(record.get("last_name"))
            effective_date = safe_str(record.get("effective_date"))
            first_name = safe_str(record.get("first_name"))
            gender = safe_str(record.get("gender"))
            category = safe_str(record.get("category"))
            speciality = safe_str(record.get("speciality"))
            state = safe_str(record.get("state"))
            group_npi = str(record.get("group_npi") or "")
            name = safe_str(record.get("name"))
            address_line1 = safe_str(record.get("address_line_1"))
            address_line2 = safe_str(record.get("address_line_2"))
            zip_code = str(record.get("zip_code_clean") or "")
            city = safe_str(record.get("city"))
            status = safe_str(record.get("status"))
            update = safe_str(record.get("update"))
            taxonomy_code = safe_str(record.get("taxonomy_code"))
            remarks = safe_str(record.get("remarks"))

            network = (network or "").strip().lower()
            health_plan = (health_plan or "").strip().lower()

            company_name = constants.COMPANY_MAP.get(network, {}).get(health_plan)
            if not company_name:
                print(
                    f"Could not map company for network '{network}' and health plan '{health_plan}', skipping.")
                status = "failed"
                message = "company_mapping_missing"
                output_snapshot = {"npi_number": npi or npi_number or record.get("npi"), "error": message}
                structured_log(
                    logger,
                    "company_mapping_missing",
                    stage=StageName.QUICKCAP.value,
                    task_id=metadata.task_id,
                    npi=npi or "unknown",
                )
                _record_micro_update(
                    record,
                    npi,
                    "Unable to map company for QuickCap submission",
                    extra={"network": network, "health_plan": health_plan},
                )
                continue

            print(f"Mapped Company: {company_name}")

            if current_company and current_company.lower() == company_name.lower():
                print(f"✅ Company '{company_name}' already logged in — skipping change.")
                _record_state_transition(
                    record,
                    npi,
                    NpiWlaTU.TU_LOGGED_INTO_COMPANY,
                    "Using active QuickCap company session",
                    micro_extra={"update_type":0}
                )
                try:
                    if quickcap_page.check_npi_search_field():
                        quickcap_page.enter_npi(npi_number)
                        quickcap_page.click_search_button()
                    else:
                        quickcap_page.ensure_credentialing_tab()
                        quickcap_page.choose_credentialing_tab()
                        quickcap_page.choose_practitioner_data()
                        quickcap_page.enter_npi(npi_number)
                        quickcap_page.click_search_button()
                except Exception as e:
                    print(e)

                try:
                    print(f"Handling Quick Add / Edit for {npi_number}")
                    if not quickcap_page.is_edit_button_available():
                        quickcap_page.click_quick_add_button()
                        quickcap_page.switch_to_new_window1()
                    else:
                        # time.sleep(5)
                        quickcap_page.click_edit_button()
                        quickcap_page.switch_to_new_window1()
                        print("Provider Setup")
                        quickcap_page.click_provider_button()
                        provider_id = quickcap_page.provider_table_rows()
                        quickcap_page.click_add_provider()
                        quickcap_page.switch_to_new_window1()
                        quickcap_page.enter_provider_letter(provider_id)
                        quickcap_page.enter_last_name(last_name or "")
                        quickcap_page.enter_first_name(first_name or "")
                        full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                            "%m/%d/%Y")
                        quickcap_page.enter_effective_date(full_date)
                        quickcap_page.select_contract_type1("CONTRACT FEE FOR SERVICE")
                        quickcap_page.select_speciality1(network)
                        quickcap_page.select_payment_type("FEE FOR SERVICE")
                        quickcap_page.enter_contract_from_date(full_date)
                        quickcap_page.select_provider_type_dropdown1(category, network, speciality)
                        quickcap_page.select_account1("0000-000 DEFAULT")
                        quickcap_page.select_template1(company_name)
                        events.emit_npi_event(
                            task_id=metadata.task_id,
                            stage=StageName.QUICKCAP,
                            npi=npi,
                            status="in_progress",
                            attempt=attempt,
                            stage_run_id=stage_run_id,
                            input_snapshot={"last_name": last_name, "first_name": first_name, "network": network},
                        )
                        print("Organization linking")
                        quickcap_page.click_organization()
                        quickcap_page.switch_to_new_window1()
                        quickcap_page.enter_npi_org(group_npi)
                        quickcap_page.click_search_npi()
                        success = quickcap_page.click_org_id(npi_number, address_line1)
                        if not success:
                            remarks_txt = "Org ID not found"
                            enriched: List[Dict] = [
                                {
                                    "address_line1": address_line1,
                                    "npi": npi_number,
                                    "update": 0,
                                    "effective_date": effective_date,
                                    "health_plan": health_plan,
                                    "update_status": 5,
                                    "remarks": remarks_txt
                                }
                            ]
                            data1 = {
                                "task_id": metadata.task_id,
                                "stage": StageName.QUICKCAP.value,
                                "failed": failures,
                                "records": enriched
                            }
                            post_webhook(metadata, StageName.QUICKCAP, data1)
                            """
                            TODO Yash: update task unit
                            Org is not found 
                            """
                            print(f"NPI {npi_number} failed due to missing Org ID.\n")
                            status = "failed"
                            message = "org_id_not_found"
                            output_snapshot = {"npi_number": npi_number or npi, "error": message}
                            events.emit_npi_event(
                                task_id=metadata.task_id,
                                stage=StageName.QUICKCAP,
                                npi=npi or "unknown",
                                status="completed" if status == "completed" else "failed",
                                attempt=attempt,
                                stage_run_id=stage_run_id,
                                input_snapshot=record,
                                output_snapshot=output_snapshot,
                                artifacts=[],
                                message=message,
                            )
                            continue
                        quickcap_page.switch_to_new_window1()
                        quickcap_page.click_add_new_location()
                        quickcap_page.enter_name1(name)
                        quickcap_page.enter_address2(address_line1 or "")
                        quickcap_page.enter_address_line2(address_line2 or "")
                        quickcap_page.select_state1("FL - FLORIDA")
                        quickcap_page.enter_zip1(zip_code or "")
                        quickcap_page.enter_city1(city or "")
                        quickcap_page.click_primary()
                        quickcap_page.click_save1()
                        events.emit_npi_event(
                            task_id=metadata.task_id,
                            stage=StageName.QUICKCAP,
                            npi=npi,
                            status="in_progress",
                            attempt=attempt,
                            stage_run_id=stage_run_id,
                            input_snapshot={"address_line1": address_line1,"address_line2": address_line2,"zip_code": zip_code},
                        )
                        if quickcap_page.driver.current_window_handle != main_window:
                            quickcap_page.driver.close()
                            quickcap_page.driver.switch_to.window(main_window)
                        print("Healthplan entry")
                        quickcap_page.enter_npi(npi_number)
                        quickcap_page.click_search_button()
                        quickcap_page.click_edit_button()
                        # time.sleep(3)
                        quickcap_page.switch_to_new_window()
                        quickcap_page.click_provider_button()
                        success = quickcap_page.click_edit_for_healthplan(provider_id)
                        if not success:
                            remarks_txt = "Address already added"
                            enriched: List[Dict] = [
                                {
                                    "address_line1": address_line1,
                                    "npi": npi_number,
                                    "update": 0,
                                    "effective_date": effective_date,
                                    "health_plan": health_plan,
                                    "update_status": 2,
                                    "remarks": remarks_txt
                                }
                            ]
                            data1 = {
                                "task_id": metadata.task_id,
                                "stage": StageName.QUICKCAP.value,
                                "failed": failures,
                                "records": enriched
                            }
                            post_webhook(metadata, StageName.QUICKCAP, data1)
                            """
                            TODO Yash: update task unit
                            address already added 
                            """
                            status = "completed"
                            message = "Address already added"
                            output_snapshot = {"npi_number": npi_number or npi, "error": message}
                            events.emit_npi_event(
                                task_id=metadata.task_id,
                                stage=StageName.QUICKCAP,
                                npi=npi or "unknown",
                                status="completed" if status == "completed" else "failed",
                                attempt=attempt,
                                stage_run_id=stage_run_id,
                                input_snapshot=record,
                                output_snapshot=output_snapshot,
                                artifacts=[],
                                message=message,
                            )
                            if quickcap_page.driver.current_window_handle != main_window:
                                quickcap_page.driver.close()
                                quickcap_page.driver.switch_to.window(main_window)
                            continue
                        """
                        TODO Yash: update task unit
                        Provider added successfully through Edit button 
                        """
                        quickcap_page.click_healthplan_panel()
                        quickcap_page.switch_to_new_window1()
                        full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                            "%m/%d/%Y")
                        quickcap_page.enter_membership_date(full_date or "")
                        quickcap_page.click_plus_button()
                        quickcap_page.click_save_healthplan()
                        """
                        TODO Yash: update task unit
                        healthplan added successfully  
                        """
                        quickcap_page.driver.close()
                        events.emit_npi_event(
                            task_id=metadata.task_id,
                            stage=StageName.QUICKCAP,
                            npi=npi,
                            status="in_progress",
                            attempt=attempt,
                            stage_run_id=stage_run_id,
                            input_snapshot={"effective_date": effective_date, "health_plan": health_plan},
                            message="Healthplan entry",
                        )
                        print("Taxonomy entry")
                        quickcap_page.switch_to_new_window()
                        quickcap_page.click_other_ids()
                        quickcap_page.click_add_plus()
                        quickcap_page.select_taxonomy("TAXONOMY - TAXONOMY")
                        quickcap_page.click_provider_id(provider_id)
                        quickcap_page.enter_taxonomy_code(taxonomy_code or "")
                        quickcap_page.click_save_taxonomy()
                        """
                        TODO Yash: update task unit
                        taxonomy added successfully  
                        """
                        if quickcap_page.driver.current_window_handle != main_window:
                            quickcap_page.driver.close()
                            quickcap_page.driver.switch_to.window(main_window)

                        enriched: List[Dict] = [
                            {
                                "address_line1": address_line1,
                                "npi": npi_number,
                                "update": 0,
                                "effective_date": effective_date,
                                "health_plan": health_plan,
                                "update_status": 2,
                            }
                        ]
                        data1 = {
                            "task_id": metadata.task_id,
                            "stage": StageName.QUICKCAP.value,
                            "failed": failures,
                            "records": enriched
                        }
                        post_webhook(metadata, StageName.QUICKCAP, data1)
                        print(f" NPI {npi_number} processed successfully.\n")
                        message = "Address added successfully"
                        output_snapshot = {"npi_number": npi_number or npi, "status": "submitted"}
                        events.emit_npi_event(
                            task_id=metadata.task_id,
                            stage=StageName.QUICKCAP,
                            npi=npi,
                            status="in_progress",
                            attempt=attempt,
                            stage_run_id=stage_run_id,
                            input_snapshot=record,
                            output_snapshot=output_snapshot,
                            message=message,
                        )
                        continue
                except TimeoutException:
                    print("Timed out waiting for search results.")
                    status = "failed"
                    message = "timeout"
                    output_snapshot = {"npi_number": npi or npi_number, "error": message}

                selected_category = constants.CATEGORY_MAP.get(category.strip(), "") if category else ""
                quickcap_page.select_category_dropdown(selected_category)
                quickcap_page.select_provider_type_dropdown(category, network, speciality)
                quickcap_page.select_speciality(network)
                quickcap_page.click_quick_add_window_npi_button(npi_number)
                quickcap_page.enter_provider_id(f"{npi_number}(A)")
                quickcap_page.enter_last_first_name(last_name or "", first_name or "")
                gender_map = {
                    "Male": "M - Male", "M": "M - Male",
                    "Female": "F - Female", "F": "F - Female"
                }
                selected_gender = gender_map.get(gender.strip(), "") if gender else ""
                quickcap_page.select_gender(selected_gender)
                full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime("%m/%d/%Y")
                quickcap_page.enter_contract_from_date(full_date)
                quickcap_page.select_contract_type("CONTRACT FEE FOR SERVICE")
                quickcap_page.select_payment_type("FEE FOR SERVICE")
                quickcap_page.select_account("0000-000 DEFAULT")
                events.emit_npi_event(
                    task_id=metadata.task_id,
                    stage=StageName.QUICKCAP,
                    npi=npi,
                    status="in_progress",
                    attempt=attempt,
                    stage_run_id=stage_run_id,
                    input_snapshot={"last_name": last_name, "first_name": first_name, "network": network},
                )
                quickcap_page.click_organization()
                quickcap_page.switch_to_new_window1()
                quickcap_page.enter_npi_org(group_npi)
                quickcap_page.click_search_npi()
                # time.sleep(3)
                success = quickcap_page.click_org_id(npi_number,
                                                     address_line1)  # Need to add WebDriver Wait here inside the pages
                if not success:
                    remarks_txt = "Org ID not found"
                    enriched: List[Dict] = [
                        {
                            "address_line1": address_line1,
                            "npi": npi_number,
                            "update": 0,
                            "effective_date": effective_date,
                            "health_plan": health_plan,
                            "update_status": 5,
                            "remarks": remarks_txt
                        }
                    ]
                    data1 = {
                        "task_id": metadata.task_id,
                        "stage": StageName.QUICKCAP.value,
                        "failed": failures,
                        "records": enriched
                       }
                    post_webhook(metadata, StageName.QUICKCAP, data1)
                    """
                    TODO Yash: update task unit
                    org id not found 
                    """
                    status = "failed"
                    message = "org_id_not_found"
                    output_snapshot = {"npi_number": npi_number or npi, "error": message}
                    events.emit_npi_event(
                        task_id=metadata.task_id,
                        stage=StageName.QUICKCAP,
                        npi=npi or "unknown",
                        status="completed" if status == "completed" else "failed",
                        attempt=attempt,
                        stage_run_id=stage_run_id,
                        input_snapshot=record,
                        output_snapshot=output_snapshot,
                        artifacts=[],
                        message=message,
                    )
                    continue
                quickcap_page.switch_to_previous_window()
                quickcap_page.select_practice_type("GRP - GROUP")
                quickcap_page.enter_name(name)
                quickcap_page.enter_address1(address_line1 or "")
                quickcap_page.enter_address_line_2(address_line2 or "")
                state_value = constants.STATE_DROPDOWN_MAP.get(state.strip(), "")
                quickcap_page.select_state(state_value)
                quickcap_page.enter_city(city or "")
                quickcap_page.enter_zip(zip_code or "")
                quickcap_page.select_contract_template(company_name)
                # time.sleep(3)
                quickcap_page.click_save()
                """
                TODO Yash: update task unit
                npi added successfully 
                """
                events.emit_npi_event(
                    task_id=metadata.task_id,
                    stage=StageName.QUICKCAP,
                    npi=npi,
                    status="in_progress",
                    attempt=attempt,
                    stage_run_id=stage_run_id,
                    input_snapshot={"address_line1": address_line1, "address_line2": address_line2,
                                    "zip_code": zip_code},
                )
                if quickcap_page.driver.current_window_handle != main_window:
                    quickcap_page.driver.close()
                    quickcap_page.driver.switch_to.window(main_window)
                quickcap_page.enter_npi(npi_number)
                quickcap_page.click_search_button()
                quickcap_page.click_edit_button()
                # time.sleep(3)
                quickcap_page.switch_to_new_window()
                quickcap_page.click_provider_button()
                quickcap_page.click_edit_for_healthplan_for_A()
                quickcap_page.click_healthplan_panel()
                quickcap_page.switch_to_new_window1()
                full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                    "%m/%d/%Y")
                quickcap_page.enter_membership_date(full_date or "")
                quickcap_page.click_plus_button()
                quickcap_page.click_save_healthplan()
                """
                TODO Yash: update task unit
                healthplan added successfully 
                """
                quickcap_page.driver.close()
                events.emit_npi_event(
                    task_id=metadata.task_id,
                    stage=StageName.QUICKCAP,
                    npi=npi,
                    status="in_progress",
                    attempt=attempt,
                    stage_run_id=stage_run_id,
                    input_snapshot={"effective_date": effective_date, "health_plan": health_plan},
                    message="Healthplan entry",
                )
                quickcap_page.switch_to_new_window()
                quickcap_page.click_other_ids()
                quickcap_page.click_add_plus()
                quickcap_page.select_taxonomy("TAXONOMY - TAXONOMY")
                quickcap_page.click_provider_id_for_A()
                quickcap_page.enter_taxonomy_code(taxonomy_code or "")
                quickcap_page.click_save_taxonomy()
                """
                TODO Yash: update task unit
                taxonomy added successfully 
                """
                if quickcap_page.driver.current_window_handle != main_window:
                    quickcap_page.driver.close()
                    quickcap_page.driver.switch_to.window(main_window)
                enriched: List[Dict] = [
                    {
                        "address_line1": address_line1,
                        "npi": npi_number,
                        "update": 0,
                        "effective_date": effective_date,
                        "health_plan": health_plan,
                        "update_status": 2

                    }
                ]
                data1 = {
                    "task_id": metadata.task_id,
                    "stage": StageName.QUICKCAP.value,
                    "failed": failures,
                    "records": enriched
                }
                post_webhook(metadata, StageName.QUICKCAP, data1)
                """
                TODO Yash: update task unit
                address already added 
                """
                message = "Address added successfully"
                output_snapshot = {"npi_number": npi_number or npi, "status": "submitted"}
                events.emit_npi_event(
                    task_id=metadata.task_id,
                    stage=StageName.QUICKCAP,
                    npi=npi,
                    status="in_progress",
                    attempt=attempt,
                    stage_run_id=stage_run_id,
                    input_snapshot=record,
                    output_snapshot=output_snapshot,
                    message=message,
                )
                continue
            quickcap_page.store_main_window()
            quickcap_page.click_change_company()
            quickcap_page.switch_to_new_window1()
            quickcap_page.choose_company(company_name)
            # quickcap_page.get_company_xpath("DNSHUMANA")
            # time.sleep(3)
            quickcap_page.enter_username_in_company_prompt("autoprocess@pns-mgmt.com")
            quickcap_page.enter_password_in_company_prompt("Pns@#111125")
            quickcap_page.click_login_button_in_company_prompt()
            """
            TODO Yash: update task unit
             change company
            """
            # time.sleep(3)
            quickcap_page.switch_to_main()
            current_company = company_name
            _record_state_transition(
                record,
                npi,
                NpiWlaTU.TU_LOGGED_INTO_COMPANY,
                "Switched company in QuickCap",
            )

            try:
                # quickcap_page.expand_menu_if_cigna(company_name="Cigna")
                if quickcap_page.is_access_denied():
                    quickcap_page.driver.back()
                    # time.sleep(2)
                    # try again expanding menu
                    # quickcap_page.expand_menu_if_cigna(company_name="Cigna")
                if quickcap_page.check_npi_search_field():
                    quickcap_page.enter_npi(npi_number)
                    quickcap_page.click_search_button()
                    # time.sleep(5)
                else:
                    quickcap_page.ensure_credentialing_tab()
                    quickcap_page.choose_credentialing_tab()
                    quickcap_page.choose_practitioner_data()
                    # time.sleep(5)
                    quickcap_page.enter_npi(npi_number)
                    quickcap_page.click_search_button()
                    # time.sleep(5)
            except Exception as e:
                raise

            try:
                if not quickcap_page.is_edit_button_available():
                    # time.sleep(3)
                    quickcap_page.click_quick_add_button()
                    quickcap_page.switch_to_new_window1()
                else:
                    quickcap_page.click_edit_button()
                    # time.sleep(3)
                    quickcap_page.switch_to_new_window1()
                    quickcap_page.click_provider_button()
                    provider_id = quickcap_page.provider_table_rows()
                    quickcap_page.click_add_provider()
                    quickcap_page.switch_to_new_window()
                    quickcap_page.enter_provider_letter(provider_id)
                    quickcap_page.enter_last_name(last_name or "")
                    quickcap_page.enter_first_name(first_name or "")
                    full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                        "%m/%d/%Y")
                    quickcap_page.enter_effective_date(full_date)
                    quickcap_page.select_contract_type1("CONTRACT FEE FOR SERVICE")
                    quickcap_page.select_speciality1(network)
                    quickcap_page.select_payment_type("FEE FOR SERVICE")
                    quickcap_page.enter_contract_from_date(full_date)
                    quickcap_page.select_provider_type_dropdown1(category, network, speciality)
                    quickcap_page.select_account1("0000-000 DEFAULT")
                    quickcap_page.select_template1(company_name)
                    events.emit_npi_event(
                        task_id=metadata.task_id,
                        stage=StageName.QUICKCAP,
                        npi=npi,
                        status="in_progress",
                        attempt=attempt,
                        stage_run_id=stage_run_id,
                        input_snapshot={"last_name": last_name, "first_name": first_name, "network": network},
                    )
                    quickcap_page.click_organization()
                    quickcap_page.switch_to_new_window1()
                    quickcap_page.enter_npi_org(group_npi)
                    quickcap_page.click_search_npi()
                    success = quickcap_page.click_org_id(npi_number, address_line1)
                    if not success:
                        remarks_txt = "Org ID not found"
                        enriched: List[Dict] = [
                            {
                                "address_line1": address_line1,
                                "npi": npi_number,
                                "update": 0,
                                "effective_date": effective_date,
                                "health_plan": health_plan,
                                "update_status": 5,
                                "remarks": remarks_txt,

                            }
                        ]
                        data1 = {
                            "task_id": metadata.task_id,
                            "stage": StageName.QUICKCAP.value,
                            "failed": failures,
                            "records": enriched
                        }
                        post_webhook(metadata, StageName.QUICKCAP, data1)
                        """
                        TODO Yash: update task unit
                        org id not found 
                        """
                        print(f"NPI {npi_number} failed due to missing Org ID.\n")
                        status = "failed"
                        message = "org_id_not_found"
                        output_snapshot = {"npi_number": npi_number or npi, "error": message}
                        events.emit_npi_event(
                            task_id=metadata.task_id,
                            stage=StageName.QUICKCAP,
                            npi=npi or "unknown",
                            status="completed" if status == "completed" else "failed",
                            attempt=attempt,
                            stage_run_id=stage_run_id,
                            input_snapshot=record,
                            output_snapshot=output_snapshot,
                            artifacts=[],
                            message=message,
                        )
                        continue
                    quickcap_page.switch_to_previous_window()
                    quickcap_page.click_add_new_location()
                    quickcap_page.enter_name1(name)
                    quickcap_page.enter_address2(address_line1 or "")
                    quickcap_page.enter_address_line2(address_line2 or "")
                    state_value = constants.STATE_DROPDOWN_MAP.get(state.strip(), "")
                    quickcap_page.select_state1(state_value)
                    quickcap_page.enter_zip1(zip_code or "")
                    quickcap_page.enter_city1(city or "")
                    quickcap_page.click_primary()
                    quickcap_page.click_save1()

                    events.emit_npi_event(
                        task_id=metadata.task_id,
                        stage=StageName.QUICKCAP,
                        npi=npi,
                        status="in_progress",
                        attempt=attempt,
                        stage_run_id=stage_run_id,
                        input_snapshot={"address_line1": address_line1, "address_line2": address_line2,
                                        "zip_code": zip_code},
                    )
                    if quickcap_page.driver.current_window_handle != main_window:
                        quickcap_page.driver.close()
                        quickcap_page.driver.switch_to.window(main_window)
                    quickcap_page.enter_npi(npi_number)
                    quickcap_page.click_search_button()
                    quickcap_page.click_edit_button()
                    # time.sleep(3)
                    quickcap_page.switch_to_new_window()
                    quickcap_page.click_provider_button()
                    success = quickcap_page.click_edit_for_healthplan(provider_id)
                    if not success:
                        remarks_txt = "Address already added"
                        enriched: List[Dict] = [
                            {
                                "address_line1": address_line1,
                                "npi": npi_number,
                                "update": 0,
                                "effective_date": effective_date,
                                "health_plan": health_plan,
                                "update_status": 2,
                                "remarks": remarks_txt
                            }
                        ]
                        data1 = {
                            "task_id": metadata.task_id,
                            "stage": StageName.QUICKCAP.value,
                            "failed": failures,
                            "records": enriched
                        }
                        post_webhook(metadata, StageName.QUICKCAP, data1)
                        """
                       TODO Yash: update task unit
                       address alrady added
                       """
                        status = "completed"
                        message = "Address already added"
                        output_snapshot = {"npi_number": npi_number or npi, "error": message}
                        events.emit_npi_event(
                            task_id=metadata.task_id,
                            stage=StageName.QUICKCAP,
                            npi=npi or "unknown",
                            status="completed" if status == "completed" else "failed",
                            attempt=attempt,
                            stage_run_id=stage_run_id,
                            input_snapshot=record,
                            output_snapshot=output_snapshot,
                            artifacts=[],
                            message=message,
                        )
                        if quickcap_page.driver.current_window_handle != main_window:
                            quickcap_page.driver.close()
                            quickcap_page.driver.switch_to.window(main_window)
                        continue
                    """
                   TODO Yash: update task unit
                   npi added
                   """
                    quickcap_page.click_healthplan_panel()

                    quickcap_page.switch_to_new_window1()
                    full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                        "%m/%d/%Y")
                    quickcap_page.enter_membership_date(full_date or "")
                    quickcap_page.click_plus_button()
                    quickcap_page.click_save_healthplan()
                    """
                   TODO Yash: update task unit
                   healthplan added
                   """
                    quickcap_page.driver.close()
                    events.emit_npi_event(
                        task_id=metadata.task_id,
                        stage=StageName.QUICKCAP,
                        npi=npi,
                        status="in_progress",
                        attempt=attempt,
                        stage_run_id=stage_run_id,
                        input_snapshot={"effective_date": effective_date, "health_plan": health_plan},
                        message="Healthplan entry",
                    )
                    quickcap_page.switch_to_new_window()
                    quickcap_page.click_other_ids()
                    quickcap_page.click_add_plus()
                    quickcap_page.select_taxonomy("TAXONOMY - TAXONOMY")
                    quickcap_page.click_provider_id(provider_id)
                    quickcap_page.enter_taxonomy_code(taxonomy_code or "")
                    quickcap_page.click_save_taxonomy()
                    """
                   TODO Yash: update task unit
                   taxonomy added
                   """
                    if quickcap_page.driver.current_window_handle != main_window:
                        quickcap_page.driver.close()
                        quickcap_page.driver.switch_to.window(main_window)
                    enriched: List[Dict] = [
                        {
                            "address_line1": address_line1,
                            "npi": npi_number,
                            "update": 0,
                            "effective_date": effective_date,
                            "health_plan": health_plan,
                            "update_status": 2

                        }
                    ]
                    data1 = {
                        "task_id": metadata.task_id,
                        "stage": StageName.QUICKCAP.value,
                        "failed": failures,
                        "records": enriched
                    }
                    post_webhook(metadata, StageName.QUICKCAP, data1)
                    # db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update(
                    #     {"status": 2}, synchronize_session=False
                    # )
                    # db.query(NPIAddress).filter(
                    #     NPIAddress.address_line1 == address_line1,
                    #     NPIAddress.npi == npi_number,
                    #     NPIAddress.update == 0
                    # ).update({"update": 1}, synchronize_session=False)
                    # db.commit()
                    message = "Address added successfully"
                    output_snapshot = {"npi_number": npi_number or npi, "status": "submitted"}
                    events.emit_npi_event(
                        task_id=metadata.task_id,
                        stage=StageName.QUICKCAP,
                        npi=npi,
                        status="in_progress",
                        attempt=attempt,
                        stage_run_id=stage_run_id,
                        input_snapshot=record,
                        output_snapshot=output_snapshot,
                        message=message,
                    )
                    continue

            except Exception as e:
                status = "failed"
                message = str(e)
                output_snapshot = {"npi_number": npi_number or npi, "error": message}
                structured_log(
                    logger,
                    "quickcap_internal_exception",
                    stage=StageName.QUICKCAP.value,
                    task_id=metadata.task_id,
                    npi=npi or "unknown",
                    error=str(e),
                )
                break

            selected_category = constants.CATEGORY_MAP.get(category.strip(), "") if category else ""
            quickcap_page.select_category_dropdown(selected_category)
            quickcap_page.select_provider_type_dropdown(category, network, speciality)
            quickcap_page.select_speciality(network)
            quickcap_page.click_quick_add_window_npi_button(npi_number)
            quickcap_page.enter_provider_id(f"{npi_number}(A)")
            quickcap_page.enter_last_first_name(last_name or "", first_name or "")
            gender_map = {
                "Male": "M - Male", "M": "M - Male",
                "Female": "F - Female", "F": "F - Female"
            }
            selected_gender = gender_map.get(gender.strip(), "") if gender else ""
            quickcap_page.select_gender(selected_gender)
            full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime("%m/%d/%Y")
            quickcap_page.enter_contract_from_date(full_date)
            quickcap_page.select_contract_type("CONTRACT FEE FOR SERVICE")
            quickcap_page.select_payment_type("FEE FOR SERVICE")
            quickcap_page.select_account("0000-000 DEFAULT")
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.QUICKCAP,
                npi=npi,
                status="in_progress",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot={"last_name": last_name, "first_name": first_name, "network": network},
            )
            quickcap_page.click_organization()
            quickcap_page.switch_to_new_window1()
            quickcap_page.enter_npi_org(group_npi)
            quickcap_page.click_search_npi()
            success = quickcap_page.click_org_id(npi_number, address_line1)
            if not success:
                remarks_txt = "Org ID not found"
                enriched: List[Dict] = [
                    {
                        "address_line1": address_line1,
                        "npi": npi_number,
                        "update": 0,
                        "effective_date": effective_date,
                        "health_plan": health_plan,
                        "update_status": 5,
                        "remarks": remarks_txt

                    }
                ]
                data1 = {
                    "task_id": metadata.task_id,
                    "stage": StageName.QUICKCAP.value,
                    "failed": failures,
                    "records": enriched
                }
                post_webhook(metadata, StageName.QUICKCAP, data1)
                status = "failed"
                message = "org_id_not_found"
                output_snapshot = {"npi_number": npi_number or npi, "error": message}
                events.emit_npi_event(
                    task_id=metadata.task_id,
                    stage=StageName.QUICKCAP,
                    npi=npi or "unknown",
                    status="completed" if status == "completed" else "failed",
                    attempt=attempt,
                    stage_run_id=stage_run_id,
                    input_snapshot=record,
                    output_snapshot=output_snapshot,
                    artifacts=[],
                    message=message,
                )
                continue
            quickcap_page.switch_to_previous_window()
            quickcap_page.select_practice_type("GRP - GROUP")
            quickcap_page.enter_name(name)
            quickcap_page.enter_address1(address_line1 or "")
            quickcap_page.enter_address_line_2(address_line2 or "")
            state_value = constants.STATE_DROPDOWN_MAP.get(state.strip(), "")
            quickcap_page.select_state(state_value)
            quickcap_page.enter_city(city or "")
            quickcap_page.enter_zip(zip_code or "")
            quickcap_page.select_contract_template(company_name)
            quickcap_page.click_save()
            """
           TODO Yash: update task unit
           npi added
           """
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.QUICKCAP,
                npi=npi,
                status="in_progress",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot={"address_line1": address_line1, "address_line2": address_line2, "zip_code": zip_code},
            )
            quickcap_page.accept_alert()
            quickcap_page.dismiss_alert()
            quickcap_page.driver.close()
            quickcap_page.switch_to_new_window1()
            quickcap_page.switch_back_to_main()
            quickcap_page.enter_npi(npi_number)
            quickcap_page.click_search_button()
            quickcap_page.click_edit_button()
            # time.sleep(3)
            quickcap_page.switch_to_new_window()
            quickcap_page.click_provider_button()
            quickcap_page.click_edit_for_healthplan_for_A()
            quickcap_page.click_healthplan_panel()
            """
           TODO Yash: update task unit
           heathplan added(quick add)
           """
            quickcap_page.switch_to_new_window1()
            full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                "%m/%d/%Y")
            quickcap_page.enter_membership_date(full_date or "")
            quickcap_page.click_plus_button()
            quickcap_page.click_save_healthplan()
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.QUICKCAP,
                npi=npi,
                status="in_progress",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot={"effective_date": effective_date, "health_plan": health_plan},
                message="Healthplan entry",
            )
            quickcap_page.driver.close()
            quickcap_page.switch_to_new_window()
            quickcap_page.click_other_ids()
            quickcap_page.click_add_plus()
            quickcap_page.select_taxonomy("TAXONOMY - TAXONOMY")
            quickcap_page.click_provider_id_for_A()
            quickcap_page.enter_taxonomy_code(taxonomy_code or "")
            quickcap_page.click_save_taxonomy()
            """
           TODO Yash: update task unit
           taxonomy added(quick add)
           """
            if quickcap_page.driver.current_window_handle != main_window:
                quickcap_page.driver.close()
                quickcap_page.driver.switch_to.window(main_window)
            enriched: List[Dict] = [
                {
                    "address_line1": address_line1,
                    "npi": npi_number,
                    "update": 0,
                    "effective_date": effective_date,
                    "health_plan": health_plan,
                    "update_status": 2,
                }
            ]
            data1 = {
                "task_id": metadata.task_id,
                "stage": StageName.QUICKCAP.value,
                "failed": failures,
                "records": enriched
            }
            post_webhook(metadata, StageName.QUICKCAP, data1)
            message = "Address added successfully"
            output_snapshot = {"npi_number": npi_number or npi, "status": "submitted"}
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.QUICKCAP,
                npi=npi,
                status="in_progress",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot=record,
                output_snapshot=output_snapshot,
                message=message,
            )
            continue

            quickcap_page.driver_close()


            # result = processor.process(record)
            # processed.append(result)
            screenshot = artifacts.capture_screenshot(
                driver, metadata, StageName.QUICKCAP, f"success_{npi_number}"
            )
            stage_result.artifacts.append(screenshot)
            structured_log(
                logger,
                "record_complete",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi={npi_number},
            )
            output_snapshot = {"npi_number": npi_number or npi, "status": "submitted"}
        except QuickcapValidationError as exc:
            failure_entry = {"npi_number": npi or record.get("npi"), "error": exc.reason or str(exc)}
            failures.append(failure_entry)
            stage_result.artifacts.append(
                artifacts.capture_screenshot(driver, metadata, StageName.QUICKCAP, f"validation_failure_{npi or 'unknown'}")
            )
            structured_log(
                logger,
                "record_validation_failure",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=npi or "unknown",
                error=exc.reason,
            )
            status = "failed"
            message = exc.reason or str(exc)
            output_snapshot = failure_entry
            if exc.reason == "org_id_not_found":
                _record_state_transition(
                    record,
                    npi,
                    NpiWlaTU.TU_ERROR_ORG_ID_NOT_FOUND,
                    "Organization ID not found in QuickCap",
                    micro_extra={"error": message,"update_type":3},
                )
            else:
                _record_micro_update(
                    record,
                    npi,
                    "Validation failure during QuickCap processing",
                    extra={"error": message,"update_type":3},
                )
        except Exception as exc:  # pragma: no cover
            failures.append({"npi_number": npi or record.get("npi"), "error": str(exc)})
            stage_result.artifacts.append(
                artifacts.capture_screenshot(driver, metadata, StageName.QUICKCAP, f"failure_{npi or 'unknown'}")
            )
            structured_log(
                logger,
                "record_failure",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=npi or "unknown",
                error=str(exc),
            )
            status = "failed"
            message = str(exc)
            output_snapshot = {"npi_number": npi or record.get("npi"), "error": message}
            _record_micro_update(
                record,
                npi,
                "Unexpected exception during QuickCap processing",
                extra={"error": message},
            )
        finally:
            structured_log(
                logger,
                "record_finished",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=npi or "unknown",
                status=status,
            )
            events.emit_npi_event(
                task_id=metadata.task_id,
                stage=StageName.QUICKCAP,
                npi=npi or "unknown",
                status="completed" if status == "completed" else "failed",
                attempt=attempt,
                stage_run_id=stage_run_id,
                input_snapshot=record,
                output_snapshot=output_snapshot,
                artifacts=[],
                message=message,
            )
            if status == "completed":
                _record_state_transition(
                    record,
                    npi,
                    NpiWlaTU.TU_UPDATE_STATUS_ON_MONDAY,
                    "QuickCap submission completed",
                    micro_extra={"update_type":1}
                )
            else:
                _record_micro_update(
                    record,
                    npi,
                    "QuickCap submission failed",
                    extra={"error": message or "unknown","update_type":3},
                )

    payload = {
        "task_id": metadata.task_id,
        "stage": StageName.QUICKCAP.value,
        "processed": processed,
        "failed": failures,
    }
    post_webhook(metadata, StageName.QUICKCAP, payload)
    """
   TODO Yash: update task unit
   complete
   """
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
