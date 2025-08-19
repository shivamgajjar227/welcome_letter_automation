import time
from time import sleep
from sqlalchemy.orm import Session
import pytest
import constants
import pages
from datetime import datetime
from conftest import monday_test
from db.session import SessionLocal
from models.pr_site_data import PRSiteData
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import allure
from pages.quickcap_page import QuickcapPage

global_npis_to_process = []

@allure.feature("Monday Data Grabbing")
@allure.story("Taking Not Started data from Monday.com")
def test_monday(monday_test):
    monday_test.login("autoprocess@pns-mgmt.com","@VEnger200@@@@")
    monday_test.click_welcome_letter_qc()
    npis = monday_test.get_pr_site_npis()
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

@allure.feature("PR Site Data Grabbing")
@allure.story("Taking NPI Details From PR Site")
def test_pr_site(pr_sites_test):
    db = SessionLocal()
    try:
        npi_records = db.query(PRSiteData).filter(PRSiteData.status == 0).all()
        print("📄 Found NPI records with status 0:", [r.npi_number for r in npi_records])

        for record in npi_records:
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
            # print("Group NPI:", group_npi)
            # print("Tax ID:", cleaned_tax_id)

            # npi_number = group_npi.split('-')[-1].strip()

            record.last_name = last_name
            record.first_name = first_name
            record.gender = gender
            record.network = network
            record.city = city
            record.state = state
            record.zip_code = cleaned_zip_code
            record.category = category
            record.taxonomy_code = taxnonomy_code
            # record.group_npi = npi_number
            record.status = 1  # mark as completed

            db.commit()
            print(" All records updated successfully.")

            pr_sites_test.hover_over_practice_menu()
            npi = str(record.npi_number)
            pr_sites_test.enter_npi_search(npi)
            pr_sites_test.click_search_npi()
            time.sleep(10)
            group_npi = pr_sites_test.get_group_npi()
            # pr_sites_test.select_click_for_tax_id()
            # tax_id = pr_sites_test.get_tax_id()
            pr_sites_test.get_ind_npi_list_with_grp_npi_locations(record)
            print("Group NPI:", group_npi)
            npi_number = group_npi.split('-')[-1].strip()
            record.group_npi = npi_number

    except Exception as e:
        db.rollback()
        print(" Error in test_pr_site:", e)
    finally:
        db.close()

# def test_company_change(quickcap_test_case):
#
#     quickcap_test_case.click_company()
#     quickcap_test_case.login("autoprocess@pns-mgmt.com", "Pns@072025")
#     for i in range(3):
#         quickcap_test_case.click_change_company()
#         quickcap_test_case.switch_to_new_window()
#         quickcap_test_case.get_company_xpath("DNSHUMANA")
#         time.sleep(3)
#         quickcap_test_case.enter_username_in_company_prompt("autoprocess@pns-mgmt.com")
#         quickcap_test_case.enter_password_in_company_prompt("Pns@072025")
#         quickcap_test_case.click_login_button_in_company_prompt()
#         time.sleep(3)
#         quickcap_test_case.switch_back_to_main()

# def test_sql(sql_server_test):
#     db = SessionLocal()
#
#     try:
#         npis = db.query(PRSiteData.npi_number).filter(PRSiteData.status == 1).all()
#
#         # time.sleep(3)
#         sql_server_test.click_credential()
#         # time.sleep(3)
#         sql_server_test.click_provider_report()
#         # time.sleep(3)
#         sql_server_test.click_pml_report()
#         # time.sleep(3)
#         sql_server_test.switch_to_report_iframe()
#         for (npi,) in npis:
#             print(f"Searching report for NPI: {npi}")
#             sql_server_test.enter_npi_search(str(npi))
#             sql_server_test.click_report_view()
#             # time.sleep(3)
#             address = sql_server_test.get_address()
#             record = db.query(PRSiteData).filter(PRSiteData.npi_number == npi,PRSiteData.status == 1).first()
#             if record:
#                 record.address = address
#                 db.commit()
#                 print(f" Address saved for NPI {npi}")
#             else:
#                 print(f" NPI {npi} not found in DB.")
#
#
#     finally:
#         db.close()

@allure.feature("QC Data Updating")
@allure.story("Updating data on QC for valid NPIs")
def test_qc(quickcap_test):

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

            company_name = constants.COMPANY_MAP.get(network, {}).get(health_plan)
            if not company_name:
                print(
                    f"Could not map company for network '{data.network}' and health plan '{data.health_plan}', skipping.")
                continue
            print(f" Mapped Company: {company_name}")

            if current_company and current_company.lower() == company_name.lower():
                print(f"✅ Company '{company_name}' already logged in — skipping change.")
                try:
                    if quickcap_test.check_npi_search_field():
                        quickcap_test.enter_npi(data.npi_number)
                        quickcap_test.click_search_button()
                    else:
                        quickcap_test.choose_credentialing_tab()
                        quickcap_test.choose_practitioner_data()
                        quickcap_test.enter_npi(data.npi_number)
                        quickcap_test.click_search_button()
                except Exception as e:
                    print(e)
                try:
                    # Wait for either "No data found" OR at least one table row
                    WebDriverWait(quickcap_test.driver, 5).until(
                        lambda d: "No data found" in d.page_source or
                                  len(d.find_elements(By.XPATH, "//table//tr[td]")) > 0
                    )

                    if "No data found" in quickcap_test.driver.page_source:
                        print("No data found — clicking Quick Add.")
                        quickcap_test.click_quick_add_button()
                    else:
                        time.sleep(5)
                        quickcap_test.click_edit_button()
                        quickcap_test.switch_to_new_window()
                        quickcap_test.click_provider_button()
                        quickcap_test.click_add_provider()
                        quickcap_test.switch_to_new_window()
                        next_location = QuickcapPage.get_next_location_letter(quickcap_test.driver)
                        print(f"Next available location: {next_location}")
                        quickcap_test.enter_last_name(data.last_name or "")
                        full_date = datetime.strptime(data.effective_date.strip() + " 2025", "%b %d %Y").strftime(
                            "%m/%d/%Y")
                        quickcap_test.enter_effective_date(full_date)
                        quickcap_test.select_contract_type1("PENDING")
                        quickcap_test.select_speciality1(data.network)
                        quickcap_test.select_payment_type("FEE FOR SERVICE")
                        quickcap_test.enter_contract_from_date(full_date)
                        quickcap_test.select_provider_type_dropdown1()
                        quickcap_test.select_account1("0000-000 DEFAULT")
                        quickcap_test.select_template1()
                        quickcap_test.click_organization()
                        quickcap_test.switch_to_new_window1()
                        quickcap_test.enter_npi_org(data.group_npi)
                        quickcap_test.click_search_npi()
                        quickcap_test.click_org_id()
                        quickcap_test.switch_to_previous_window()
                        quickcap_test.click_add_new_location()
                        quickcap_test.enter_name1("LAKE DERMATOLOGY PA")
                        quickcap_test.enter_address2(data.address or "")
                        quickcap_test.select_state1("FL - FLORIDA")
                        quickcap_test.enter_zip1(data.zip_code)
                        quickcap_test.enter_city1(data.city or "")
                        quickcap_test.click_primary()
                        quickcap_test.click_cancel1()

                        quickcap_test.driver.close()
                        quickcap_test.switch_to_new_window1()

                        data.status = 2
                        db.commit()
                        print(f" NPI {data.npi_number} processed successfully.\n")
                        continue

                except TimeoutException:
                    print("Timed out waiting for search results.")

                quickcap_test.click_quick_add_button()
                quickcap_test.switch_to_new_window()
                selected_category = constants.CATEGORY_MAP.get(data.category.strip(), "") if data.category else ""
                quickcap_test.select_category_dropdown(selected_category)
                quickcap_test.select_provider_type_dropdown()
                quickcap_test.click_quick_add_window_npi_button(data.npi_number)
                quickcap_test.select_speciality1(data.network)
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
                quickcap_test.switch_to_new_window1()
                quickcap_test.enter_npi_org(data.group_npi)
                quickcap_test.click_search_npi()
                # time.sleep(3)
                quickcap_test.click_org_id()  # Need to add WebDriver Wait here inside the pages
                quickcap_test.switch_to_previous_window()
                # quickcap_test.select_org_from_popup("TEST ORG NAME")
                # quickcap_test.driver.close()
                # quickcap_test.switch_to_previous_window()
                # org_name = quickcap_test.get_org_name()
                quickcap_test.select_practice_type("GRP - GROUP")
                quickcap_test.enter_name("LAKE DERMATOLOGY PA")
                quickcap_test.enter_address1(data.address or "")
                state_value = constants.STATE_DROPDOWN_MAP.get(data.state.strip(), "")
                quickcap_test.select_state("FL - FLORIDA")
                quickcap_test.enter_city(data.city or "")
                quickcap_test.enter_zip(data.zip_code)
                quickcap_test.select_template()
                # time.sleep(3)
                # quickcap_test.click_save()
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

            quickcap_test.store_main_window()
            quickcap_test.click_change_company()
            quickcap_test.switch_to_new_window1()
            quickcap_test.choose_company(company_name)
            # quickcap_test.get_company_xpath("DNSHUMANA")
            # time.sleep(3)
            quickcap_test.enter_username_in_company_prompt("autoprocess@pns-mgmt.com")
            quickcap_test.enter_password_in_company_prompt("Pns@072025")
            quickcap_test.click_login_button_in_company_prompt()
            # time.sleep(3)
            quickcap_test.switch_to_main()
            current_company = company_name
            # print(f" Mapped Company: {company_name}")
            # quickcap_test.choose_company(company_name)
            # quickcap_test.login("autoprocess@pns-mgmt.com", "Pns@072025")
            # quickcap_test.click_agree_inside_iframe()
            # quickcap_test.click_cancel()
            # quickcap_test.click_links_handler()
            time.sleep(5)
            if quickcap_test.check_npi_search_field():
                quickcap_test.enter_npi(data.npi_number)
                quickcap_test.click_search_button()
            else:
                quickcap_test.choose_credentialing_tab()
                quickcap_test.choose_practitioner_data()
                time.sleep(5)
                quickcap_test.enter_npi(data.npi_number)
                quickcap_test.click_search_button()
            try:
                WebDriverWait(quickcap_test.driver, 5).until(
                    lambda d: "No data found" in d.page_source or
                              len(d.find_elements(By.XPATH, "//table//tr[td]")) > 0
                )

                if "No data found" in quickcap_test.driver.page_source:
                    print("No data found — clicking Quick Add.")
                    quickcap_test.click_quick_add_button()
                else:
                    time.sleep(5)
                    quickcap_test.click_edit_button()
                    time.sleep(5)
                    quickcap_test.switch_to_new_window()
                    quickcap_test.click_provider_button()
                    quickcap_test.click_add_provider()
                    quickcap_test.switch_to_new_window()
                    next_location = QuickcapPage.get_next_location_letter(quickcap_test.driver)
                    print(f"Next available location: {next_location}")
                    quickcap_test.enter_last_name(data.last_name or "")
                    full_date = datetime.strptime(data.effective_date.strip() + " 2025", "%b %d %Y").strftime(
                        "%m/%d/%Y")
                    quickcap_test.enter_effective_date(full_date)
                    quickcap_test.select_contract_type1("PENDING")
                    quickcap_test.select_speciality1(data.network)
                    quickcap_test.select_payment_type("FEE FOR SERVICE")
                    quickcap_test.enter_contract_from_date(full_date)
                    quickcap_test.select_provider_type_dropdown1()
                    quickcap_test.select_account1("0000-000 DEFAULT")
                    quickcap_test.select_template1()
                    quickcap_test.click_organization()
                    quickcap_test.switch_to_new_window1()
                    quickcap_test.enter_npi_org(data.group_npi)
                    quickcap_test.click_search_npi()
                    quickcap_test.click_org_id()
                    quickcap_test.switch_to_previous_window()
                    quickcap_test.click_add_new_location()
                    quickcap_test.enter_name1("LAKE DERMATOLOGY PA")
                    quickcap_test.enter_address2(data.address or "")
                    quickcap_test.select_state1("FL - FLORIDA")
                    quickcap_test.enter_zip1(data.zip_code)
                    quickcap_test.enter_city1(data.city or "")
                    quickcap_test.click_primary()
                    quickcap_test.click_cancel1()

                    quickcap_test.driver.close()
                    quickcap_test.switch_to_new_window1()

                    data.status = 2
                    db.commit()
                    print(f" NPI {data.npi_number} processed successfully.\n")

                    continue

            except Exception as e:
                print(e)

            quickcap_test.switch_to_new_window()
            selected_category = constants.CATEGORY_MAP.get(data.category.strip(), "") if data.category else ""
            quickcap_test.select_category_dropdown(selected_category)
            quickcap_test.select_provider_type_dropdown()
            quickcap_test.click_quick_add_window_npi_button(data.npi_number)
            # quickcap_test.select_primary_speciality_dropdown2("Dermatology")
            quickcap_test.select_speciality1(data.network)
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
            quickcap_test.switch_to_new_window1()
            quickcap_test.enter_npi_org(data.group_npi)
            quickcap_test.click_search_npi()
            # time.sleep(3)
            quickcap_test.click_org_id() #Need to add WebDriver Wait here inside the pages
            quickcap_test.switch_to_previous_window()
            # quickcap_test.select_org_from_popup("TEST ORG NAME")
            # quickcap_test.driver.close()
            # quickcap_test.switch_to_previous_window()
            # org_name = quickcap_test.get_org_name()
            quickcap_test.select_practice_type("GRP - GROUP")
            quickcap_test.enter_name("LAKE DERMATOLOGY PA")
            quickcap_test.enter_address1(data.address or "")
            state_value = constants.STATE_DROPDOWN_MAP.get(data.state.strip(), "")
            quickcap_test.select_state("FL - FLORIDA")
            quickcap_test.enter_city(data.city or "")
            quickcap_test.enter_zip(data.zip_code)
            quickcap_test.select_contract_template()
            # time.sleep(3)
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
            continue
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
        # quickcap_test.switch_to_new_window()

    finally:
        db.close()


def test_monday_status(monday_test):
    monday_test.login("autoprocess@pns-mgmt.com","@VEnger200@@@@")
    monday_test.click_welcome_letter_qc()

    db: Session = SessionLocal()
    try:
        npi_records = db.query(PRSiteData).filter(PRSiteData.status == 2).all()

        if not npi_records:
            print("No NPI records with status = 2.")
            return

        first_iteration = True  # Flag to track first iteration

        for record in npi_records:
            try:
                if first_iteration:
                    monday_test.click_search_button()
                    first_iteration = False

                monday_test.enter_npi_button(record.npi_number)
                time.sleep(2)
                monday_test.click_not_started()
                monday_test.click_done_button()
                time.sleep(2)
                monday_test.click_cross_button()
                time.sleep(2)
                record.status = 3
                db.commit()
                print(f" NPI {record.npi_number} processed successfully.\n")

            except Exception as e:
                print(f"Error processing NPI {record.npi_number}: {str(e)}")

        monday_test.driver.close()

    finally:
        db.close()


# def test_company_change(quickcap_test_case):
#
#     quickcap_test_case.click_company()
#     quickcap_test_case.login("autoprocess@pns-mgmt.com", "Pns@072025")
#     for i in range(3):
#         quickcap_test_case.click_change_company()
#         quickcap_test_case.switch_to_new_window()
#         quickcap_test_case.get_company_xpath("DNSHUMANA")
#         time.sleep(3)
#         quickcap_test_case.enter_username_in_company_prompt("autoprocess@pns-mgmt.com")
#         quickcap_test_case.enter_password_in_company_prompt("Pns@072025")
#         quickcap_test_case.click_login_button_in_company_prompt()
#         time.sleep(3)
#         quickcap_test_case.switch_back_to_main()
#
# def test_qc(quickcap_test):
#
#     COMPANY_MAP = {
#         "dermatology": {
#             "cigna": "DNS Cigna",
#             "aetna": "DNS Aetna",
#             "oxford": "DNS Oxford",
#             "florida blue": "DNS BCBS",
#             "humana": "DNS Humana",
#             "uhc": "DNS UHC",
#         },
#         "pain management": {
#             "cigna": "PM Cigna",
#             "aetna": "PM Aetna",
#             "oxford": "PM Oxford",
#             "florida blue": "PM BCBS",
#             "humana": "PM Humana",
#             "uhc": "PM UHC",
#         },
#         "podiatry": {
#             "cigna": "PNS Cigna",
#             "aetna": "PNS Aetna",
#             "oxford": "PNS Oxford",
#             "florida blue": "PNS BCBS",
#             "humana": "PNS Humana",
#             "uhc": "PNS UHC",
#         },
#         "orthopedic": {
#             "cigna": "ONS Cigna",
#             "aetna": "ONS Aetna",
#             "oxford": "ONS Oxford",
#             "florida blue": "ONS BCBS",
#             "humana": "ONS Humana",
#             "uhc": "ONS UHC",
#         },
#     }
#
#     CATEGORY_MAP = {
#         "ARNP": "ARNP - ARNP",
#         "CRNA": "CRNA - CRNA",
#         "CRNP": "CRNP - CRNP",
#         "DC": "DC - CHIROPRACTORS",
#         "DDS": "DDS - DDS",
#         "DO": "DO - OSTEOPATHIC PHYSICIAN",
#         "DPM": "DPM - DPM",
#         "FNP": "FNP - FAMILY NURSE PRACTITIONER",
#         "LM": "LM - LICENCE MIDWIFE",
#         "MD": "MD - MD",
#         "MID": "MID - MIDWIFE",
#         "ND": "ND - NATUROPATHIC DOCTOR",
#         "NMW": "NMW - NURSE MIDWIFE",
#         "NP": "NP - NURSE PRACITIONER",
#         "PA": "PA - PHYSICIAN ASSISTANT",
#         "PHD": "PHD - PHD",
#         "PT": "PT - PHYSICAL THERAPY",
#         "RD": "RD - REGISTERED DIETICIAN",
#         "RN": "RN - REGISTERED NURSE",
#         "PA-C": "PA - PHYSICIAN ASSISTANT",
#     }
#
#     STATE_DROPDOWN_MAP = {
#         "Alabama": "AL - ALABAMA",
#         "Alaska": "AK - ALASKA",
#         "Arizona": "AZ - ARIZONA",
#         "Arkansas": "AR - ARKANSAS",
#         "California": "CA - CALIFORNIA",
#         "Colorado": "CO - COLORADO",
#         "Connecticut": "CT - CONNECTICUT",
#         "Delaware": "DE - DELAWARE",
#         "D.C.": "DC - D.C.",
#         "Florida": "FL - FLORIDA",
#         "Georgia": "GA - GEORGIA",
#         "Hawaii": "HI - HAWAII",
#         "Idaho": "ID - IDAHO",
#         "Illinois": "IL - ILLINOIS",
#         "Indiana": "IN - INDIANA",
#         "Iowa": "IA - IOWA",
#         "Kansas": "KS - KANSAS",
#         "Kentucky": "KY - KENTUCKY",
#         "Louisiana": "LA - LOUISIANA",
#         "Maine": "ME - MAINE",
#         "Maryland": "MD - MARYLAND",
#         "Massachusetts": "MA - MASSACHUSETTS",
#         "Michigan": "MI - MICHIGAN",
#         "Minnesota": "MN - MINNESOTA",
#         "Mississippi": "MS - MISSISSIPPI",
#         "Missouri": "MO - MISSOURI",
#         "Montana": "MT - MONTANA",
#         "Nebraska": "NE - NEBRASKA",
#         "Nevada": "NV - NEVADA",
#         "New Hampshire": "NH - NEW HAMPSHIRE",
#         "New Jersey": "NJ - NEW JERSEY",
#         "New Mexico": "NM - NEW MEXICO",
#         "New York": "NY - NEW YORK",
#         "North Carolina": "NC - NORTH CAROLINA",
#         "North Dakota": "ND - NORTH DAKOTA",
#         "Ohio": "OH - OHIO",
#         "Oklahoma": "OK - OKLAHOMA",
#         "Oregon": "OR - OREGON",
#         "Pennsylvania": "PA - PENNSYLVANIA",
#         "Puerto Rico": "PR - PUERTO RICO",
#         "Rhode Island": "RI - RHODE ISLAND",
#         "South Carolina": "SC - SOUTH CAROLINA",
#         "South Dakota": "SD - SOUTH DAKOTA",
#         "Tennessee": "TN - TENNESSEE",
#         "Texas": "TX - TEXAS",
#         "Utah": "UT - UTAH",
#         "Vermont": "VT - VERMONT",
#         "Virginia": "VA - VIRGINIA",
#         "Virgin Islands": "VI - VIRGIN ISLANDS",
#         "Washington": "WA - WASHINGTON",
#         "West Virginia": "WV - WEST VIRGINIA",
#         "Wisconsin": "WI - WISCONSIN",
#         "Wyoming": "WY - WYOMING",
#     }
#     db = SessionLocal()
#
#     try:
#         quickcap_test.click_company()
#         quickcap_test.login("autoprocess@pns-mgmt.com", "Pns@072025")
#
#         npi_records = db.query(PRSiteData).filter(PRSiteData.status == 1).all()
#
#         if not npi_records:
#             print("No NPI records with status = 1.")
#             return
#         current_company = None
#
#         for data in npi_records:
#
#             print(f"\n Processing NPI: {data.npi_number} | Health Plan: {data.health_plan} | Network: {data.network}")
#
#             network = (data.network or "").strip().lower()
#             health_plan = (data.health_plan or "").strip().lower()
#
#             company_name = COMPANY_MAP.get(network, {}).get(health_plan)
#             if not company_name:
#                 print(
#                     f"Could not map company for network '{data.network}' and health plan '{data.health_plan}', skipping.")
#                 continue
#             print(f" Mapped Company: {company_name}")
#
#             if current_company and current_company.lower() == company_name.lower():
#                 print(f"✅ Company '{company_name}' already logged in — skipping change.")
#                 quickcap_test.choose_credentialing_tab()
#                 quickcap_test.choose_practitioner_data()
#                 quickcap_test.enter_npi(data.npi_number)
#                 quickcap_test.click_search_button()
#
#
#
#     finally:
#         db.close()


