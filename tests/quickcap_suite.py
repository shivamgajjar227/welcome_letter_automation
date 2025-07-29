import time
from time import sleep
from sqlalchemy.orm import Session
import pytest
import pages
from datetime import datetime
from conftest import monday_test
from pages import global_variables
import cruds
from db.session import SessionLocal
from models.pr_site_data import PRSiteData
import json



from cruds import pr_site_data
global_npis_to_process = []

def test_monday(monday_test):
    monday_test.login("autoprocess@pns-mgmt.com","@VEnger200@@@@")
    monday_test.click_welcome_letter_qc()
    npis =monday_test.get_pr_site_npis()
    print(npis)

    db: Session = SessionLocal()

    try:
        for entry in npis:
            new_row = PRSiteData(
                npi_number=entry.get("npi_number"),
                effective_date=entry.get("effective_date"),
                health_plan=entry.get("health_plan"),
                lines_of_business=entry.get("lines_of_business"),
                status=0
            )
            db.add(new_row)
            print(f"Inserted row: {entry}")

        db.commit()
        print("All NPIs inserted into pr_site_data table.")
    except Exception as e:
        db.rollback()
        print(" Error inserting data:", e)
    finally:
        db.close()


def test_pr_site(pr_sites_test):
    db = SessionLocal()
    try:
        # Step 1: Get NPI records where status = 0
        npi_records = db.query(PRSiteData).filter(PRSiteData.status == 0).all()
        print("📄 Found NPI records with status 0:", [r.npi_number for r in npi_records])

        pr_sites_test.hover_over_update_menu()

        for record in npi_records:
            npi = str(record.npi_number)

            pr_sites_test.enter_npi_search(npi)
            pr_sites_test.click_search_npi()
            time.sleep(3)
            pr_sites_test.click_search_npi()
            time.sleep(3)

            last_name = pr_sites_test.get_last_name()
            first_name = pr_sites_test.get_first_name()
            gender = pr_sites_test.get_gender()
            npi_number = pr_sites_test.get_npi_number()
            city = pr_sites_test.get_city()
            state = pr_sites_test.get_state()
            zip_code = pr_sites_test.get_zip_code()
            category = pr_sites_test.get_category()

            print("✅ Updating:", npi)
            print("Last Name:", last_name)
            print("First Name:", first_name)
            print("Gender:", gender)
            print("City:", city)
            print("State:", state)
            print("Zip Code:", zip_code)
            print("Category:", category)

            # Step 2: Update the existing DB row
            record.last_name = last_name
            record.first_name = first_name
            record.gender = gender
            record.city = city
            record.state = state
            record.zip_code = zip_code
            record.category = category
            record.status = 1  # mark as completed

        db.commit()
        print("✅ All records updated successfully.")

    except Exception as e:
        db.rollback()
        print("❌ Error in test_pr_site:", e)
    finally:
        db.close()


def test_qc(quickcap_test):
    db = SessionLocal()
    try:
        data_list = db.query(PRSiteData).filter(PRSiteData.status == 1).all()

        if not data_list:
            print("No data found with status = 1")
            return

        COMPANY_MAP = {
            "aetna": "DNS Aetna",
            "ons aetna": "ONS Aetna",
            "dns aetna": "DNS Aetna",
            "pns aetna": "PNS Aetna",

            "avmed": "DNS AvMed",
            "dns avmed": "DNS AvMed",
            "pns avmed": "PNS AvMed",

            "bcbs": "DNS BCBS",
            "florida blue": "DNS BCBS",
            "dns bcbs": "DNS BCBS",
            "pns bcbs": "PNS BCBS",

            "cigna": "DNS Cigna",
            "dns cigna": "DNS Cigna",
            "pns cigna": "PNS Cigna",
            "pmc cigna": "PMC Cigna",
            "ons cigna": "ONS Cigna",

            "conviva": "Conviva Orthopedics",

            "devoted": "DNS Devoted",
            "dns devoted": "DNS Devoted",
            "pns devoted": "PNS Devoted",
            "pmd devoted": "PMD Devoted",

            "humana": "DNS Humana",
            "dns humana": "DNS Humana",
            "pm humana": "PM Humana",
            "pns humana": "PNS Humana",
            "ons humana": "ONS HUMANA",

            "magellan": "DNS Magellan",
            "pns magellan": "PNS Magellan",

            "peoples health": "PNS Peoples Health",

            "simply": "DNS Simply",
            "dns simply": "DNS Simply",
            "pms simply": "PMS Simply",
            "pmc simply": "PMC Simply",
            "pns simply": "PNS Simply",
            "pmd simply ffs": "PMD Simply FFS",

            "wellcare": "DNS WellCare",
        }

        for data in data_list:
            selected_company = COMPANY_MAP.get(data.health_plan, "").strip().lower()
            quickcap_test.choose_company(selected_company)
            quickcap_test.login("autoprocess@pns-mgmt.com", "Pns@072025")
            quickcap_test.click_agree()
            time.sleep(3)
            quickcap_test.choose_credentialing_tab()
            quickcap_test.choose_practitioner_data()
            # quickcap_test.enter_npi(npi)
            for data in data_list:
                npi = str(data.npi_number).strip()
                if not npi.isdigit():
                    print(f"⚠ Skipping invalid NPI: {npi}")
                    continue
                print(f"➡️ Processing NPI: {npi}")
                quickcap_test.click_quick_add_button()
                quickcap_test.switch_to_new_window()
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
                    "NP": "NP - NURSE PRACTITIONER",
                    "OPT": "OPT - OPTOMETRIST",
                    "PA": "PA - PHYSICIAN ASSISTANT",
                    "PHD": "PHD - PHD",
                    "PT": "PT - PHYSICAL THERAPY",
                    "RD": "RD - REGISTERED DIETICIAN",
                    "RN": "RN - REGISTERED NURSE"
                }
                selected_category = CATEGORY_MAP.get(data.category.strip(), "") if data.category else ""
                quickcap_test.select_category_dropdown(selected_category)

                quickcap_test.click_quick_add_window_npi_button(npi)
                quickcap_test.select_provider_type_dropdown("PHYSICIAN EXTENDER")
                quickcap_test.enter_provider_id("1234")
                # quickcap_test.select_primary_speciality_dropdown("DM - DERMATOLOGY MOHS ONLY")

                quickcap_test.enter_last_first_name(data.last_name or "", data.first_name or "")
                # quickcap_test.select_suffix(data.category or "")
                gender_map = {
                    "Male": "M - Male",
                    "M": "M - Male",
                    "Female": "F - Female",
                    "F": "F - Female"
                }
                selected_gender = gender_map.get(data.gender.strip(), "") if data.gender else ""
                quickcap_test.select_gender(selected_gender)
                quickcap_test.select_contract_type("CONTRACT CAPITATION")
                raw_date = data.effective_date.strip()
                full_date = datetime.strptime(raw_date + " 2025", "%b %d %Y").strftime("%m/%d/%Y")
                quickcap_test.enter_contract_from_date(full_date)
                quickcap_test.select_payment_type("FEE FOR SERVICE")
                quickcap_test.select_account("0000-000 DEFAULT")
                quickcap_test.click_organization()
                quickcap_test.switch_to_new_window()
                quickcap_test.enter_npi_org(npi)
                quickcap_test.click_search_npi()
                quickcap_test.select_org_from_popup("TEST ORG NAME")
                quickcap_test.driver.close()
                quickcap_test.switch_to_previous_window()
                quickcap_test.select_organizational_type("PRIMARY")
                quickcap_test.enter_org_effective_from("07/22/2025")
                quickcap_test.select_availability("Available")
                quickcap_test.select_practice_type("GRP - GROUP")
                quickcap_test.enter_name("ABC")
                quickcap_test.enter_address1("XYZ")
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
                dropdown_value = STATE_DROPDOWN_MAP.get(data.state.strip(), "")
                quickcap_test.select_state(dropdown_value)
                quickcap_test.enter_city(data.city or "")
                quickcap_test.enter_zip(data.zip_code or "")
                quickcap_test.driver.close()
                quickcap_test.switch_to_new_window()
                data.status = 2
                db.commit()

                print("Data added to QC and status updated.")

    finally:
        db.close()






