import time
from time import sleep
from sqlalchemy.orm import Session
import pytest
import pages
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
    time.sleep(3)
    monday_test.click_welcome_letter_qc()
    npis =monday_test.get_pr_site_npis()
    print(npis)
    time.sleep(3)

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
        time.sleep(3)

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

            print("✅ Updating:", npi)
            print("Last Name:", last_name)
            print("First Name:", first_name)
            print("Gender:", gender)
            print("City:", city)
            print("State:", state)
            print("Zip Code:", zip_code)

            # Step 2: Update the existing DB row
            record.last_name = last_name
            record.first_name = first_name
            record.gender = gender
            record.city = city
            record.state = state
            record.zip_code = zip_code
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

        quickcap_test.choose_company()
        quickcap_test.login("autoprocess@pns-mgmt.com", "Pns@072025")
        time.sleep(3)
        quickcap_test.choose_credentialing_tab()
        time.sleep(3)
        quickcap_test.choose_practitioner_data()
        time.sleep(3)
        # quickcap_test.enter_npi(npi)
        for data in data_list:
            npi = str(data.npi_number).strip()
            if not npi.isdigit():
                print(f"⚠ Skipping invalid NPI: {npi}")
                continue
            print(f"➡️ Processing NPI: {npi}")
            quickcap_test.click_quick_add_button()
            quickcap_test.switch_to_new_window()
            quickcap_test.select_category_dropdown("CRNA - CRNA")
            time.sleep(3)

            quickcap_test.click_quick_add_window_npi_button(npi)
            time.sleep(3)
            quickcap_test.select_provider_type_dropdown("PHYSICIAN EXTENDER")
            time.sleep(3)
            quickcap_test.enter_provider_id("1234")
            # quickcap_test.select_primary_speciality_dropdown("DM - DERMATOLOGY MOHS ONLY")

            quickcap_test.enter_last_first_name(data.last_name or "", data.first_name or "")
            time.sleep(3)
            gender_map = {
                "Male": "M - Male",
                "M": "M - Male",
                "Female": "F - Female",
                "F": "F - Female"
            }
            selected_gender = gender_map.get(data.gender.strip(), "") if data.gender else ""
            quickcap_test.select_gender(selected_gender)
            time.sleep(3)
            quickcap_test.enter_birthdate("07/19/2025")
            time.sleep(5)
            quickcap_test.select_contract_type("CONTRACT CAPITATION")
            quickcap_test.enter_contract_from_date("07/20/2025")
            quickcap_test.select_payment_type("FEE FOR SERVICE")
            quickcap_test.select_account("0000-000 DEFAULT")
            time.sleep(3)
            quickcap_test.click_organization()
            quickcap_test.switch_to_new_window()
            quickcap_test.enter_npi_org(npi)
            quickcap_test.click_search_npi()
            quickcap_test.select_org_from_popup("TEST ORG NAME")
            quickcap_test.driver.close()
            quickcap_test.switch_to_previous_window()
            time.sleep(3)
            quickcap_test.select_organizational_type("PRIMARY")
            quickcap_test.enter_org_effective_from("07/22/2025")
            quickcap_test.select_availability("Available")
            quickcap_test.select_practice_type("GRP - GROUP")
            quickcap_test.enter_name("ABC")
            quickcap_test.enter_address1("XYZ")
            # quickcap_test.select_state(data.state)
            quickcap_test.enter_city(data.city or "")
            quickcap_test.enter_zip(data.zip_code or "")
            time.sleep(5)
            quickcap_test.driver.close()
            quickcap_test.switch_to_new_window()
            data.status = 2
            db.commit()

            print("Data added to QC and status updated.")

    finally:
        db.close()






