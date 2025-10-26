"""Headless runner implementation for the QuickCap submission stage."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Mapping, Optional

from selenium.webdriver.remote.webdriver import WebDriver

import constants
from pages.quickcap_page import QuickcapPage

from .. import artifacts
from ..context import CredentialRef, RunnerMetadata, StageName, StageResult
from ..logging import structured_log
from ..webhooks import post_webhook, fetch_stage_payload

logger = logging.getLogger(__name__)


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


def _normalize_record(raw_record: Mapping[str, Any]) -> Dict[str, Any]:
    npi_number = str(raw_record.get("npi_number") or raw_record.get("npi") or "").strip()
    if not npi_number:
        raise QuickcapValidationError("missing_npi")

    network = str(raw_record.get("network") or "").strip()
    health_plan = str(raw_record.get("health_plan") or "").strip()
    company_override = str(raw_record.get("company") or "").strip()
    company_name = company_override or _map_company(network, health_plan)
    if not company_name:
        raise QuickcapValidationError("company_mapping_missing")

    address = _select_primary_address(raw_record)
    address_line1 = (
        address.get("address_line_1")
        or raw_record.get("address_line1")
        or raw_record.get("address_line_1")
    )
    if not address_line1:
        raise QuickcapValidationError("missing_address_line1")

    address_line2 = address.get("address_line_2") or raw_record.get("address_line2") or ""
    city = address.get("city") or raw_record.get("city") or ""
    state = address.get("state") or raw_record.get("state") or ""
    zip_code = (
        address.get("zipcode")
        or address.get("zip_code")
        or raw_record.get("zip_code")
        or raw_record.get("postal_code")
        or ""
    )
    state_value = _map_state(state)

    effective_date = str(raw_record.get("effective_date") or "").strip()
    contract_date = _format_effective_date(effective_date)

    group_npi = str(raw_record.get("group_npi") or "").strip()
    if not group_npi:
        raise QuickcapValidationError("missing_group_npi")

    category = str(raw_record.get("category") or "").strip()
    speciality = str(raw_record.get("speciality") or "").strip()
    gender = str(raw_record.get("gender") or "").strip()
    taxonomy_code = str(raw_record.get("taxonomy_code") or "").strip()
    practice_name = (
        str(raw_record.get("name") or "")
        or str(raw_record.get("practice_name") or "")
        or str(raw_record.get("group_name") or "")
        or "Unknown Practice"
    )

    return {
        "npi_number": npi_number,
        "network": network,
        "health_plan": health_plan,
        "company_name": company_name,
        "last_name": str(raw_record.get("last_name") or "").strip(),
        "first_name": str(raw_record.get("first_name") or "").strip(),
        "gender": _map_gender(gender),
        "raw_gender": gender,
        "category": category,
        "category_option": _map_category(category),
        "speciality": speciality,
        "effective_date": effective_date,
        "contract_date": contract_date,
        "group_npi": group_npi,
        "taxonomy_code": taxonomy_code,
        "practice_name": practice_name,
        "address_line1": address_line1,
        "address_line2": address_line2,
        "city": city,
        "state": state,
        "state_value": state_value,
        "zip_code": zip_code,
        "zip_code_clean": (address.get("zip_code_clean") or zip_code.replace("-", "")),
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

    def _ensure_company(self, company_name: str) -> None:
        if self.current_company and self.current_company.lower() == company_name.lower():
            return
        if not self.page.choose_company(company_name):
            raise QuickcapValidationError(f"company_switch_failed:{company_name}")
        self.current_company = company_name
        self.page.set_main_window_before_switching()

    def _ensure_practitioner_context(self) -> None:
        if not self.page.check_npi_search_field():
            self.page.ensure_credentialing_tab()
            self.page.choose_credentialing_tab()
        self.page.choose_practitioner_data()

    def _search_npi(self, npi: str) -> None:
        if not npi:
            raise QuickcapValidationError("missing_npi")
        self.page.enter_npi(npi)
        self.page.click_search_button()

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

    def _link_organization(self, data: Mapping[str, Any]) -> None:
        self.page.click_organization()
        self.page.switch_to_new_window1()
        self.page.enter_npi_org(data["group_npi"])
        self.page.click_search_npi()
        if not self.page.click_org_id(data["npi_number"], data["address_line1"]):
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
    payload = fetch_stage_payload(metadata, StageName.QUICKCAP)
    if not payload:
        structured_log(
            logger,
            "input_payload_missing",
            stage=StageName.QUICKCAP.value,
            task_id=metadata.task_id,
        )
        stage_result.mark_finished(success=False, error="quickcap_input_unavailable")
        return stage_result

    records: List[Dict[str, Any]] = list(payload.get("records", [])) or list(payload.get("processed", []))

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
        quickcap_page.set_main_window_before_switching()
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
        return stage_result

    processed: List[Dict] = []
    failures: List[Dict] = []
    processor = QuickcapProcessor(quickcap_page)

    for record in records:
        npi = str(record.get("npi_number") or record.get("npi") or "").strip()
        try:
            structured_log(
                logger,
                "record_start",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=npi or "unknown",
            )
            result = processor.process(record)
            processed.append(result)
            screenshot = artifacts.capture_screenshot(
                driver, metadata, StageName.QUICKCAP, f"success_{result['npi_number']}"
            )
            stage_result.artifacts.append(screenshot)
            structured_log(
                logger,
                "record_complete",
                stage=StageName.QUICKCAP.value,
                task_id=metadata.task_id,
                npi=result["npi_number"],
            )
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

    payload = {
        "task_id": metadata.task_id,
        "stage": StageName.QUICKCAP.value,
        "processed": processed,
        "failed": failures,
    }
    post_webhook(metadata, StageName.QUICKCAP, payload)

    stage_result.data["processed"] = processed
    stage_result.data["failed"] = failures
    stage_result.mark_finished(success=not failures)
    return stage_result
