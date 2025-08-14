from db.session import SessionLocal
from models.pr_site_data import PRSiteData
import time
from datetime import datetime


def test_qc(quickcap_test):

    COMPANY_MAP = {
        "dermatology": {
            "cigna": "DNS Cigna",
            "aetna": "DNS Aetna",
            "oxford": "DNS Oxford",
            "florida blue": "DNS BCBS",
            "humana": "DNS Humana",
            "uhc": "DNS UHC",
        },
        "pain management": {
            "cigna": "PM Cigna",
            "aetna": "PM Aetna",
            "oxford": "PM Oxford",
            "florida blue": "PM BCBS",
            "humana": "PM Humana",
            "uhc": "PM UHC",
        },
        "podiatry": {
            "cigna": "PNS Cigna",
            "aetna": "PNS Aetna",
            "oxford": "PNS Oxford",
            "florida blue": "PNS BCBS",
            "humana": "PNS Humana",
            "uhc": "PNS UHC",
        },
        "orthopedic": {
            "cigna": "ONS Cigna",
            "aetna": "ONS Aetna",
            "oxford": "ONS Oxford",
            "florida blue": "ONS BCBS",
            "humana": "ONS Humana",
            "uhc": "ONS UHC",
        },
    }

    CATEGORY_MAP = {
        "ARNP": "ARNP - ARNP",
        "CRNA": "CRNA - CRNA",
        "CRNP": "CRNP - CRNP",
        "DC": "DC - CHIROPRACTORS",
        "DDS": "DDS - DDS",
        "DO": "DO - OSTEOPATHIC PHYSICIAN",
        "DPM": "DPM - DPM",
        "FNP": "FNP - FAMILY NURSE PRACTITIONER",
        "LM": "LM - LICENCE MIDWIFE",
        "MD": "MD - MD",
        "MID": "MID - MIDWIFE",
        "ND": "ND - NATUROPATHIC DOCTOR",
        "NMW": "NMW - NURSE MIDWIFE",
        "NP": "NP - NURSE PRACITIONER",
        "PA": "PA - PHYSICIAN ASSISTANT",
        "PHD": "PHD - PHD",
        "PT": "PT - PHYSICAL THERAPY",
        "RD": "RD - REGISTERED DIETICIAN",
        "RN": "RN - REGISTERED NURSE",
        "PA-C": "PA - PHYSICIAN ASSISTANT",
    }

    STATE_DROPDOWN_MAP = {
        "Alabama": "AL - ALABAMA",
        "Alaska": "AK - ALASKA",
        "Arizona": "AZ - ARIZONA",
        "Arkansas": "AR - ARKANSAS",
        "California": "CA - CALIFORNIA",
        "Colorado": "CO - COLORADO",
        "Connecticut": "CT - CONNECTICUT",
        "Delaware": "DE - DELAWARE",
        "D.C.": "DC - D.C.",
        "Florida": "FL - FLORIDA",
        "Georgia": "GA - GEORGIA",
        "Hawaii": "HI - HAWAII",
        "Idaho": "ID - IDAHO",
        "Illinois": "IL - ILLINOIS",
        "Indiana": "IN - INDIANA",
        "Iowa": "IA - IOWA",
        "Kansas": "KS - KANSAS",
        "Kentucky": "KY - KENTUCKY",
        "Louisiana": "LA - LOUISIANA",
        "Maine": "ME - MAINE",
        "Maryland": "MD - MARYLAND",
        "Massachusetts": "MA - MASSACHUSETTS",
        "Michigan": "MI - MICHIGAN",
        "Minnesota": "MN - MINNESOTA",
        "Mississippi": "MS - MISSISSIPPI",
        "Missouri": "MO - MISSOURI",
        "Montana": "MT - MONTANA",
        "Nebraska": "NE - NEBRASKA",
        "Nevada": "NV - NEVADA",
        "New Hampshire": "NH - NEW HAMPSHIRE",
        "New Jersey": "NJ - NEW JERSEY",
        "New Mexico": "NM - NEW MEXICO",
        "New York": "NY - NEW YORK",
        "North Carolina": "NC - NORTH CAROLINA",
        "North Dakota": "ND - NORTH DAKOTA",
        "Ohio": "OH - OHIO",
        "Oklahoma": "OK - OKLAHOMA",
        "Oregon": "OR - OREGON",
        "Pennsylvania": "PA - PENNSYLVANIA",
        "Puerto Rico": "PR - PUERTO RICO",
        "Rhode Island": "RI - RHODE ISLAND",
        "South Carolina": "SC - SOUTH CAROLINA",
        "South Dakota": "SD - SOUTH DAKOTA",
        "Tennessee": "TN - TENNESSEE",
        "Texas": "TX - TEXAS",
        "Utah": "UT - UTAH",
        "Vermont": "VT - VERMONT",
        "Virginia": "VA - VIRGINIA",
        "Virgin Islands": "VI - VIRGIN ISLANDS",
        "Washington": "WA - WASHINGTON",
        "West Virginia": "WV - WEST VIRGINIA",
        "Wisconsin": "WI - WISCONSIN",
        "Wyoming": "WY - WYOMING",
    }
    db = SessionLocal()

    try:
        quickcap_test.click_company()
        quickcap_test.login("autoprocess@pns-mgmt.com", "Pns@072025")

        npi_records = db.query(PRSiteData).filter(PRSiteData.status == 1).all()

        if not npi_records:
            print("No NPI records with status = 1.")
            return
        current_company = None

        for data in npi_records:

            print(f"\n Processing NPI: {data.npi_number} | Health Plan: {data.health_plan} | Network: {data.network}")

            network = (data.network or "").strip().lower()
            health_plan = (data.health_plan or "").strip().lower()

            company_name = COMPANY_MAP.get(network, {}).get(health_plan)
            if not company_name:
                print(
                    f"Could not map company for network '{data.network}' and health plan '{data.health_plan}', skipping.")
                continue
            print(f" Mapped Company: {company_name}")

            if current_company and current_company.lower() == company_name.lower():
                print(f"✅ Company '{company_name}' already logged in — skipping change.")
                quickcap_test.choose_credentialing_tab()
                quickcap_test.choose_practitioner_data()
                quickcap_test.click_quick_add_button()
                quickcap_test.switch_to_new_window()
                selected_category = CATEGORY_MAP.get(data.category.strip(), "") if data.category else ""
                quickcap_test.select_category_dropdown(selected_category)
                quickcap_test.select_provider_type_dropdown()
                quickcap_test.click_quick_add_window_npi_button(data.npi_number)
                quickcap_test.select_primary_speciality_dropdown()
                quickcap_test.enter_provider_id(f"{data.npi_number}A")
                quickcap_test.enter_last_first_name(data.last_name or "", data.first_name or "")

                gender_map = {
                    "Male": "M - Male", "M": "M - Male",
                    "Female": "F - Female", "F": "F - Female"
                }
                selected_gender = gender_map.get(data.gender.strip(), "") if data.gender else ""
                quickcap_test.select_gender(selected_gender)

                full_date = datetime.strptime(data.effective_date.strip() + " 2025", "%b %d %Y").strftime("%m/%d/%Y")
                quickcap_test.enter_contract_from_date(full_date)
                quickcap_test.select_contract_type("PENDING")
                quickcap_test.select_payment_type("FEE FOR SERVICE")
                quickcap_test.select_account("0000-000 DEFAULT")
                quickcap_test.click_organization()
                quickcap_test.switch_to_new_window()
                quickcap_test.enter_npi_org(data.group_npi)
                quickcap_test.click_search_npi()
                time.sleep(3)
                quickcap_test.click_org_id()  # Need to add WebDriver Wait here inside the pages
                quickcap_test.switch_to_previous_window()
                # quickcap_test.select_org_from_popup("TEST ORG NAME")
                # quickcap_test.driver.close()
                # quickcap_test.switch_to_previous_window()
                # org_name = quickcap_test.get_org_name()
                quickcap_test.select_practice_type("GRP - GROUP")
                quickcap_test.enter_name("LAKE DERMATOLOGY PA")
                quickcap_test.enter_address1(data.address or "")
                state_value = STATE_DROPDOWN_MAP.get(data.state.strip(), "")
                quickcap_test.select_state("FL - FLORIDA")
                quickcap_test.enter_city(data.city or "")
                quickcap_test.enter_zip(data.zip_code)
                quickcap_test.select_template()
                time.sleep(3)
                # quickcap_test.click_save()
                time.sleep(3)
                quickcap_test.driver.close()
                quickcap_test.switch_to_new_window()
                # quickcap_test.cancel_button_click_quick_add()
                # quickcap_test.handle_confirmation_popup("OK")
                #
                # # Handle second confirmation popup
                # quickcap_test.handle_confirmation_popup("OK")
                #
                # # 5. Return to main window and change company
                data.status = 2
                db.commit()
                print(f" NPI {data.npi_number} processed successfully.\n")
                continue

            quickcap_test.click_change_company()
            quickcap_test.switch_to_new_window()
            quickcap_test.choose_company(company_name)
            # quickcap_test.get_company_xpath("DNSHUMANA")
            # time.sleep(3)
            quickcap_test.enter_username_in_company_prompt("autoprocess@pns-mgmt.com")
            quickcap_test.enter_password_in_company_prompt("Pns@072025")
            quickcap_test.click_login_button_in_company_prompt()
            time.sleep(3)
            quickcap_test.switch_to_new_window()
            current_company = company_name
            # print(f" Mapped Company: {company_name}")
            # quickcap_test.choose_company(company_name)
            # quickcap_test.login("autoprocess@pns-mgmt.com", "Pns@072025")
            # quickcap_test.click_agree_inside_iframe()
            # quickcap_test.click_cancel()
            # quickcap_test.click_links_handler()
            quickcap_test.choose_credentialing_tab()
            quickcap_test.choose_practitioner_data()
            quickcap_test.click_quick_add_button()
            quickcap_test.switch_to_new_window()
            selected_category = CATEGORY_MAP.get(data.category.strip(), "") if data.category else ""
            quickcap_test.select_category_dropdown(selected_category)
            quickcap_test.select_provider_type_dropdown()
            quickcap_test.click_quick_add_window_npi_button(data.npi_number)
            quickcap_test.select_primary_speciality_dropdown()
            quickcap_test.enter_provider_id(f"{data.npi_number}A")
            quickcap_test.enter_last_first_name(data.last_name or "", data.first_name or "")

            gender_map = {
                "Male": "M - Male", "M": "M - Male",
                "Female": "F - Female", "F": "F - Female"
            }
            selected_gender = gender_map.get(data.gender.strip(), "") if data.gender else ""
            quickcap_test.select_gender(selected_gender)

            full_date = datetime.strptime(data.effective_date.strip() + " 2025", "%b %d %Y").strftime("%m/%d/%Y")
            quickcap_test.enter_contract_from_date(full_date)
            quickcap_test.select_contract_type("PENDING")
            quickcap_test.select_payment_type("FEE FOR SERVICE")
            quickcap_test.select_account("0000-000 DEFAULT")
            quickcap_test.click_organization()
            quickcap_test.switch_to_new_window()
            quickcap_test.enter_npi_org(data.group_npi)
            quickcap_test.click_search_npi()
            time.sleep(3)
            quickcap_test.click_org_id() #Need to add WebDriver Wait here inside the pages
            quickcap_test.switch_to_previous_window()
            # quickcap_test.select_org_from_popup("TEST ORG NAME")
            # quickcap_test.driver.close()
            # quickcap_test.switch_to_previous_window()
            # org_name = quickcap_test.get_org_name()
            quickcap_test.select_practice_type("GRP - GROUP")
            quickcap_test.enter_name("LAKE DERMATOLOGY PA")
            quickcap_test.enter_address1(data.address or "")
            state_value = STATE_DROPDOWN_MAP.get(data.state.strip(), "")
            quickcap_test.select_state("FL - FLORIDA")
            quickcap_test.enter_city(data.city or "")
            quickcap_test.enter_zip(data.zip_code)
            quickcap_test.select_template()
            time.sleep(3)
            # quickcap_test.click_save()
            # time.sleep(3)
            quickcap_test.driver.close()
            quickcap_test.switch_to_new_window()
            # quickcap_test.cancel_button_click_quick_add()
            # quickcap_test.handle_confirmation_popup("OK")
            #
            # # Handle second confirmation popup
            # quickcap_test.handle_confirmation_popup("OK")
            #
            # # 5. Return to main window and change company
            data.status = 2
            db.commit()
            print(f" NPI {data.npi_number} processed successfully.\n")
            # quickcap_test.switch_back_to_main()
            # quickcap_test.click_change_company()
            # quickcap_test.switch_to_new_window()
            # quickcap_test.get_company_xpath("DNSHUMANA")
            # time.sleep(3)
            # quickcap_test.enter_username_in_company_prompt("autoprocess@pns-mgmt.com")
            # quickcap_test.enter_password_in_company_prompt("Pns@072025")
            # quickcap_test.click_login_button_in_company_prompt()
            # time.sleep(5)
            # quickcap_test.switch_back_to_main()
            # time.sleep(5)

        quickcap_test.driver_close()
        quickcap_test.switch_to_new_window()

    finally:
        db.close()


def test_qc(quickcap_test):

    COMPANY_MAP = {
        "dermatology": {
            "cigna": "DNS Cigna",
            "aetna": "DNS Aetna",
            "oxford": "DNS Oxford",
            "florida blue": "DNS BCBS",
            "humana": "DNS Humana",
            "uhc": "DNS UHC",
        },
        "pain management": {
            "cigna": "PM Cigna",
            "aetna": "PM Aetna",
            "oxford": "PM Oxford",
            "florida blue": "PM BCBS",
            "humana": "PM Humana",
            "uhc": "PM UHC",
        },
        "podiatry": {
            "cigna": "PNS Cigna",
            "aetna": "PNS Aetna",
            "oxford": "PNS Oxford",
            "florida blue": "PNS BCBS",
            "humana": "PNS Humana",
            "uhc": "PNS UHC",
        },
        "orthopedic": {
            "cigna": "ONS Cigna",
            "aetna": "ONS Aetna",
            "oxford": "ONS Oxford",
            "florida blue": "ONS BCBS",
            "humana": "ONS Humana",
            "uhc": "ONS UHC",
        },
    }

    CATEGORY_MAP = {
        "ARNP": "ARNP - ARNP",
        "CRNA": "CRNA - CRNA",
        "CRNP": "CRNP - CRNP",
        "DC": "DC - CHIROPRACTORS",
        "DDS": "DDS - DDS",
        "DO": "DO - OSTEOPATHIC PHYSICIAN",
        "DPM": "DPM - DPM",
        "FNP": "FNP - FAMILY NURSE PRACTITIONER",
        "LM": "LM - LICENCE MIDWIFE",
        "MD": "MD - MD",
        "MID": "MID - MIDWIFE",
        "ND": "ND - NATUROPATHIC DOCTOR",
        "NMW": "NMW - NURSE MIDWIFE",
        "NP": "NP - NURSE PRACITIONER",
        "PA": "PA - PHYSICIAN ASSISTANT",
        "PHD": "PHD - PHD",
        "PT": "PT - PHYSICAL THERAPY",
        "RD": "RD - REGISTERED DIETICIAN",
        "RN": "RN - REGISTERED NURSE",
        "PA-C": "PA - PHYSICIAN ASSISTANT",
    }

    STATE_DROPDOWN_MAP = {
        "Alabama": "AL - ALABAMA",
        "Alaska": "AK - ALASKA",
        "Arizona": "AZ - ARIZONA",
        "Arkansas": "AR - ARKANSAS",
        "California": "CA - CALIFORNIA",
        "Colorado": "CO - COLORADO",
        "Connecticut": "CT - CONNECTICUT",
        "Delaware": "DE - DELAWARE",
        "D.C.": "DC - D.C.",
        "Florida": "FL - FLORIDA",
        "Georgia": "GA - GEORGIA",
        "Hawaii": "HI - HAWAII",
        "Idaho": "ID - IDAHO",
        "Illinois": "IL - ILLINOIS",
        "Indiana": "IN - INDIANA",
        "Iowa": "IA - IOWA",
        "Kansas": "KS - KANSAS",
        "Kentucky": "KY - KENTUCKY",
        "Louisiana": "LA - LOUISIANA",
        "Maine": "ME - MAINE",
        "Maryland": "MD - MARYLAND",
        "Massachusetts": "MA - MASSACHUSETTS",
        "Michigan": "MI - MICHIGAN",
        "Minnesota": "MN - MINNESOTA",
        "Mississippi": "MS - MISSISSIPPI",
        "Missouri": "MO - MISSOURI",
        "Montana": "MT - MONTANA",
        "Nebraska": "NE - NEBRASKA",
        "Nevada": "NV - NEVADA",
        "New Hampshire": "NH - NEW HAMPSHIRE",
        "New Jersey": "NJ - NEW JERSEY",
        "New Mexico": "NM - NEW MEXICO",
        "New York": "NY - NEW YORK",
        "North Carolina": "NC - NORTH CAROLINA",
        "North Dakota": "ND - NORTH DAKOTA",
        "Ohio": "OH - OHIO",
        "Oklahoma": "OK - OKLAHOMA",
        "Oregon": "OR - OREGON",
        "Pennsylvania": "PA - PENNSYLVANIA",
        "Puerto Rico": "PR - PUERTO RICO",
        "Rhode Island": "RI - RHODE ISLAND",
        "South Carolina": "SC - SOUTH CAROLINA",
        "South Dakota": "SD - SOUTH DAKOTA",
        "Tennessee": "TN - TENNESSEE",
        "Texas": "TX - TEXAS",
        "Utah": "UT - UTAH",
        "Vermont": "VT - VERMONT",
        "Virginia": "VA - VIRGINIA",
        "Virgin Islands": "VI - VIRGIN ISLANDS",
        "Washington": "WA - WASHINGTON",
        "West Virginia": "WV - WEST VIRGINIA",
        "Wisconsin": "WI - WISCONSIN",
        "Wyoming": "WY - WYOMING",
    }
    db = SessionLocal()

    try:
        quickcap_test.click_company()
        quickcap_test.login("autoprocess@pns-mgmt.com", "Pns@072025")

        npi_records = db.query(PRSiteData).filter(PRSiteData.status == 1).all()

        if not npi_records:
            print("No NPI records with status = 1.")
            return
        current_company = None

        for data in npi_records:

            print(f"\n Processing NPI: {data.npi_number} | Health Plan: {data.health_plan} | Network: {data.network}")

            network = (data.network or "").strip().lower()
            health_plan = (data.health_plan or "").strip().lower()

            company_name = COMPANY_MAP.get(network, {}).get(health_plan)
            if not company_name:
                print(
                    f"Could not map company for network '{data.network}' and health plan '{data.health_plan}', skipping.")
                continue
            print(f" Mapped Company: {company_name}")

            if current_company and current_company.lower() == company_name.lower():
                print(f"✅ Company '{company_name}' already logged in — skipping change.")
                quickcap_test.choose_credentialing_tab()
                quickcap_test.choose_practitioner_data()
                quickcap_test.enter_npi(data.npi_number)
                quickcap_test.click_search_button()



    finally:
        db.close()
