from sqlalchemy.orm import Session
from db.session import SessionLocal
from models.pr_site_data import PRSiteData
import time


def test_pr_site(pr_sites_test):
    db = SessionLocal()
    try:
        npi_records = db.query(PRSiteData).filter(PRSiteData.status == 0).all()
        print("📄 Found NPI records with status 0:", [r.npi_number for r in npi_records])

        for record in npi_records:

            pr_sites_test.hover_over_practice_menu()
            npi = str(record.npi_number)
            pr_sites_test.enter_npi_search(npi)
            pr_sites_test.click_search_npi()
            time.sleep(10)
            group_npi = pr_sites_test.get_group_npi()
            # pr_sites_test.select_click_for_tax_id()
            # tax_id = pr_sites_test.get_tax_id()
            pr_sites_test.get_ind_npi_list_with_grp_npi_locations(record)

            pr_sites_test.hover_over_update_menuu()
            npi = str(record.npi_number)
            pr_sites_test.enter_npi_search(npi)
            pr_sites_test.click_search_npi()
            time.sleep(3)
            last_name = pr_sites_test.get_last_name()
            first_name = pr_sites_test.get_first_name()
            gender = pr_sites_test.get_gender()
            npi_number = pr_sites_test.get_npi_number()
            network = pr_sites_test.get_network()
            city = pr_sites_test.get_city()
            state = pr_sites_test.get_state()
            zip_code = pr_sites_test.get_zip_code()
            category = pr_sites_test.get_category()
            taxnonomy_code = pr_sites_test.get_taxonomy_code()

            # group_npi = pr_sites_test.test_handle_multiple_tabs()
            cleaned_zip_code = zip_code.replace("-", "") if zip_code else None
            # cleaned_tax_id = tax_id.replace("-", "") if zip_code else None

            print("✅ Updating:", npi)
            print("Last Name:", last_name)
            print("First Name:", first_name)
            print("Gender:", gender)
            print("network:", network)
            print("City:", city)
            print("State:", state)
            print("Zip Code:", cleaned_zip_code)
            print("Category:", category)
            print("taxonomy_code:", taxnonomy_code)
            print("Group NPI:", group_npi)
            # print("Tax ID:", cleaned_tax_id)

            npi_number = group_npi.split('-')[-1].strip()

            record.last_name = last_name
            record.first_name = first_name
            record.gender = gender
            record.network = network
            record.city = city
            record.state = state
            record.zip_code = cleaned_zip_code
            record.category = category
            record.taxonomy_code = taxnonomy_code
            record.group_npi = npi_number
            record.status = 1  # mark as completed

            db.commit()
            print(" All records updated successfully.")

    except Exception as e:
        db.rollback()
        print(" Error in test_pr_site:", e)
    finally:
        db.close()

def test_practice_menu_effective_date_case(pr_sites_test):
    pr_sites_test.hover_over_practice_menu()
    npi = str(1407236227)
    pr_sites_test.enter_npi_search(npi)
    pr_sites_test.click_search_npi()
    time.sleep(3)
    pr_sites_test.get_ind_npi_list_with_grp_npi_locations()
    time.sleep(10)
