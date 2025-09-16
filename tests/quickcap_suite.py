import time
from sqlalchemy.orm import Session
import pytest
from utils import safe_str
import constants
from datetime import datetime
from conftest import monday_test
from db.session import SessionLocal
from models.pr_site_data import PRSiteData
from models.npi_address import NPIAddress
from selenium.common.exceptions import TimeoutException
import allure
from selenium.webdriver.support.ui import WebDriverWait


global_npis_to_process = []


@pytest.mark.order(1)
@allure.feature("Monday Data Grabbing")
@allure.story("Taking Not Started data from Monday.com")
def test_monday(monday_test):
    with allure.step("Logging into Monday.com and fetching NPIs"):
        if monday_test.is_login_page():  # <-- only log in if needed
            monday_test.login("autoprocess@pns-mgmt.com", "@VEnger200@@@@")

    with allure.step("Clicking Welcome Letter QC"):
        monday_test.click_welcome_letter_qc()

    with allure.step("Storing NPIs from Monday.com"):
        npis = monday_test.get_pr_site_npis()
        allure.attach(str(npis),name="NPIs from Monday.com", attachment_type=allure.attachment_type.TEXT)
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

@pytest.mark.order(2)
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

            pr_sites_test.hover_over_practice_menu()
            npi = str(record.npi_number)
            pr_sites_test.enter_npi_search(npi)
            pr_sites_test.click_search_npi()
            time.sleep(15)
            group_npi = pr_sites_test.get_group_npi()
            group_name = pr_sites_test.get_group_name()
            # pr_sites_test.select_click_for_tax_id()
            # tax_id = pr_sites_test.get_tax_id()
            pr_sites_test.get_ind_npi_list_with_grp_npi_locations(record, group_npi, group_name)

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
            record.status = 1

            db.commit()
            print(" All records updated successfully.")

    except Exception as e:
            db.rollback()
            print(" Error in test_pr_site:", e)
    finally:
        db.close()

@pytest.mark.order(3)
@allure.feature("QC Data Updating")
@allure.story("Updating data on QC for valid NPIs")
def test_qc(quickcap_test):
    main_window = quickcap_test.driver.current_window_handle
    db = SessionLocal()

    try:
        quickcap_test.click_company()
        quickcap_test.login("autoprocess@pns-mgmt.com", "Pns@072025")

        npi_records = db.query(PRSiteData.network,PRSiteData.health_plan,PRSiteData.npi_number,PRSiteData.last_name,PRSiteData.effective_date,PRSiteData.gender,PRSiteData.first_name,PRSiteData.category
                              , NPIAddress.state, NPIAddress.group_npi,NPIAddress.name,NPIAddress.address_line1,NPIAddress.address_line2,NPIAddress.zip_code,NPIAddress.city,PRSiteData.status,NPIAddress.update).join(NPIAddress, PRSiteData.npi_number == NPIAddress.npi).filter(NPIAddress.update == 0).distinct(NPIAddress.zip_code).all()
        if not npi_records:
            print("No NPI records with status = 1.")
            return

        columns = [
            "network", "health_plan", "npi_number", "last_name", "effective_date",
            "gender","first_name", "category",
            "state", "group_npi", "name", "address_line1","address_line2", "zip_code", "city", "status", "update"
        ]

        current_company = None

        for row in npi_records:
            record = dict(zip(columns, row))

            network = safe_str(record["network"])
            health_plan = safe_str(record["health_plan"])
            npi_number = str(record["npi_number"] or "")
            last_name = safe_str(record["last_name"])
            effective_date = record["effective_date"]  # keep raw (date type)
            gender = safe_str(record["gender"])
            first_name = safe_str(record["first_name"])
            category = safe_str(record["category"])
            state = safe_str(record["state"])
            group_npi = str(record["group_npi"] or "")
            name = safe_str(record["name"])
            address_line1 = safe_str(record["address_line1"])
            address_line2 = safe_str(record["address_line2"])
            zip_code = str(record["zip_code"] or "")
            city = safe_str(record["city"])
            status = safe_str(record["status"])
            update = safe_str(record["update"])


            print(f"\n Processing NPI: {npi_number} | Health Plan: {health_plan} | Network: {network}")

            network = (network or "").strip().lower()
            health_plan = (health_plan or "").strip().lower()

            company_name = constants.COMPANY_MAP.get(network, {}).get(health_plan)
            if not company_name:
                print(
                    f"Could not map company for network '{network}' and health plan '{health_plan}', skipping.")
                continue
            print(f" Mapped Company: {company_name}")

            if current_company and current_company.lower() == company_name.lower():
                print(f"✅ Company '{company_name}' already logged in — skipping change.")
                try:
                    if quickcap_test.check_npi_search_field():
                        quickcap_test.enter_npi(npi_number)
                        quickcap_test.click_search_button()
                        time.sleep(5)
                    else:
                        quickcap_test.ensure_credentialing_tab()
                        quickcap_test.choose_credentialing_tab()
                        quickcap_test.choose_practitioner_data()
                        quickcap_test.enter_npi(npi_number)
                        quickcap_test.click_search_button()
                        # time.sleep(5)
                except Exception as e:
                    print(e)
                try:
                    # Wait for either "No data found" OR at least one table row
                    # WebDriverWait(quickcap_test.driver, 5).until(
                    #     lambda d: "No data found" in d.page_source or
                    #               len(d.find_elements(By.XPATH, "//table//tr[td]")) > 0
                    # )
                    # check_no_data_found = quickcap_test.check_no_data_found_text()
                    if not quickcap_test.is_edit_button_available():
                        time.sleep(3)
                        quickcap_test.click_quick_add_button()
                        quickcap_test.switch_to_new_window()
                    else:
                        time.sleep(5)
                        quickcap_test.click_edit_button()
                        quickcap_test.switch_to_new_window()
                        quickcap_test.click_provider_button()
                        provider_id = quickcap_test.provider_table_rows()
                        quickcap_test.click_add_provider()
                        quickcap_test.switch_to_new_window()
                        quickcap_test.enter_provider_letter(provider_id)
                        quickcap_test.enter_last_name(last_name or "")
                        quickcap_test.enter_first_name(first_name or "")
                        full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                            "%m/%d/%Y")
                        quickcap_test.enter_effective_date(full_date)
                        quickcap_test.select_contract_type1("PENDING")
                        quickcap_test.select_speciality1(network)
                        quickcap_test.select_payment_type("FEE FOR SERVICE")
                        quickcap_test.enter_contract_from_date(full_date)
                        quickcap_test.select_provider_type_dropdown1()
                        quickcap_test.select_account1("0000-000 DEFAULT")
                        quickcap_test.select_template1(company_name)
                        quickcap_test.click_organization()
                        quickcap_test.switch_to_new_window1()
                        quickcap_test.enter_npi_org(group_npi)
                        quickcap_test.click_search_npi()
                        success = quickcap_test.click_org_id(npi_number,address_line1)
                        if not success:
                            # Org ID not found → update failure status here
                            db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update({"status": 5})
                            db.query(NPIAddress).filter(
                                NPIAddress.address_line1 == address_line1,
                                NPIAddress.npi == npi_number
                            ).update({"update": 3})
                            db.commit()
                            print(f"NPI {npi_number} failed due to missing Org ID.\n")
                            continue

                        quickcap_test.switch_to_previous_window()
                        quickcap_test.click_add_new_location()
                        quickcap_test.enter_name1(name)
                        quickcap_test.enter_address2(address_line1 or "")
                        quickcap_test.enter_address_line2(address_line2 or "")
                        quickcap_test.select_state1("FL - FLORIDA")
                        quickcap_test.enter_zip1(zip_code)
                        quickcap_test.enter_city1(city or "")
                        quickcap_test.click_primary()
                        # quickcap_test.click_cancel1()
                        time.sleep(5)
                        quickcap_test.click_save1()

                        quickcap_test.driver.close()
                        quickcap_test.switch_to_new_window1()

                        quickcap_test.switch_to_new_window1()
                        db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update(
                            {"status": 2}, synchronize_session=False
                        )
                        db.query(NPIAddress).filter(
                            NPIAddress.address_line1 == address_line1,
                            NPIAddress.npi == npi_number,
                            NPIAddress.update == 0
                        ).update({"update": 1}, synchronize_session=False)

                        db.commit()

                        print(f" NPI {npi_number} processed successfully.\n")
                        continue

                except TimeoutException:
                    print("Timed out waiting for search results.")

                # quickcap_test.click_quick_add_button()
                # quickcap_test.switch_to_new_window()
                selected_category = constants.CATEGORY_MAP.get(category.strip(), "") if category else ""
                quickcap_test.select_category_dropdown(selected_category)
                quickcap_test.select_provider_type_dropdown()
                quickcap_test.select_primary_speciality_dropdown(network)
                quickcap_test.click_quick_add_window_npi_button(npi_number)
                # quickcap_test.select_speciality1(network)
                quickcap_test.enter_provider_id(f"{npi_number}(A)")
                quickcap_test.enter_last_first_name(last_name or "", first_name or "")

                gender_map = {
                    "Male": "M - Male", "M": "M - Male",
                    "Female": "F - Female", "F": "F - Female"
                }
                selected_gender = gender_map.get(gender.strip(), "") if gender else ""
                quickcap_test.select_gender(selected_gender)

                full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime("%m/%d/%Y")
                quickcap_test.enter_contract_from_date(full_date)
                quickcap_test.select_contract_type("PENDING")
                quickcap_test.select_payment_type("FEE FOR SERVICE")
                quickcap_test.select_account("0000-000 DEFAULT")
                quickcap_test.click_organization()
                quickcap_test.switch_to_new_window1()
                quickcap_test.enter_npi_org(group_npi)
                quickcap_test.click_search_npi()
                # time.sleep(3)
                success = quickcap_test.click_org_id(npi_number, address_line1)  # Need to add WebDriver Wait here inside the pages
                if not success:
                    # Org ID not found → update failure status here
                    db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update({"status": 5})
                    db.query(NPIAddress).filter(
                        NPIAddress.address_line1 == address_line1,
                        NPIAddress.npi == npi_number
                    ).update({"update": 3})
                    db.commit()
                    print(f" NPI {npi_number} failed due to missing Org ID.\n")
                    continue

                quickcap_test.switch_to_previous_window()
                # quickcap_test.select_org_from_popup("TEST ORG NAME")
                # quickcap_test.driver.close()
                # quickcap_test.switch_to_previous_window()
                # org_name = quickcap_test.get_org_name()
                quickcap_test.select_practice_type("GRP - GROUP")
                quickcap_test.enter_name(name)
                quickcap_test.enter_address1(address_line1 or "")
                quickcap_test.enter_address_line_2(address_line2 or "")
                state_value = constants.STATE_DROPDOWN_MAP.get(state.strip(), "")
                quickcap_test.select_state(state_value)
                quickcap_test.enter_city(city or "")
                quickcap_test.enter_zip(zip_code)
                quickcap_test.select_contract_template(company_name)
                # time.sleep(3)
                quickcap_test.click_save()

                # ✅ Always close popup safely
                if quickcap_test.driver.current_window_handle != main_window:
                    quickcap_test.driver.close()
                    quickcap_test.driver.switch_to.window(main_window)

                # quickcap_test.switch_to_new_window1()
                db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update(
                    {"status": 2}, synchronize_session=False
                )
                db.query(NPIAddress).filter(
                    NPIAddress.address_line1 == address_line1,
                    NPIAddress.npi == npi_number,
                    NPIAddress.update == 0
                ).update({"update": 1}, synchronize_session=False)

                db.commit()

                print(f" NPI {npi_number} processed successfully.\n")
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
            try:
                if quickcap_test.check_npi_search_field():
                    quickcap_test.enter_npi(npi_number)
                    quickcap_test.click_search_button()
                    time.sleep(5)
                else:
                    quickcap_test.ensure_credentialing_tab()
                    quickcap_test.choose_credentialing_tab()
                    quickcap_test.choose_practitioner_data()
                    time.sleep(5)
                    quickcap_test.enter_npi(npi_number)
                    quickcap_test.click_search_button()
                    # time.sleep(5)
            except Exception as e:
                print(e)
            try:
                # Wait for either "No data found" OR at least one table row
                # WebDriverWait(quickcap_test.driver, 5).until(
                #     lambda d: "No data found" in d.page_source or
                #               len(d.find_elements(By.XPATH, "//table//tr[td]")) > 0
                # )
                # check_no_data_found = quickcap_test.check_no_data_found_text()
                if not quickcap_test.is_edit_button_available():
                    # time.sleep(3)
                    quickcap_test.click_quick_add_button()
                    quickcap_test.switch_to_new_window()
                else:
                    quickcap_test.click_edit_button()
                    time.sleep(3)
                    quickcap_test.switch_to_new_window()
                    quickcap_test.click_provider_button()
                    provider_id = quickcap_test.provider_table_rows()
                    quickcap_test.click_add_provider()
                    quickcap_test.switch_to_new_window()
                    quickcap_test.enter_provider_letter(provider_id)
                    quickcap_test.enter_last_name(last_name or "")
                    quickcap_test.enter_first_name(first_name or "")
                    full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                        "%m/%d/%Y")
                    quickcap_test.enter_effective_date(full_date)
                    quickcap_test.select_contract_type1("PENDING")
                    quickcap_test.select_speciality1(network)
                    quickcap_test.select_payment_type("FEE FOR SERVICE")
                    quickcap_test.enter_contract_from_date(full_date)
                    quickcap_test.select_provider_type_dropdown1()
                    quickcap_test.select_account1("0000-000 DEFAULT")
                    quickcap_test.select_template1(company_name)
                    quickcap_test.click_organization()
                    quickcap_test.switch_to_new_window1()
                    quickcap_test.enter_npi_org(group_npi)
                    quickcap_test.click_search_npi()
                    success = quickcap_test.click_org_id(npi_number, address_line1)
                    if not success:
                        # Org ID not found → update failure status here
                        db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update({"status": 5})
                        db.query(NPIAddress).filter(
                            NPIAddress.address_line1 == address_line1,
                            NPIAddress.npi == npi_number
                        ).update({"update": 3})
                        db.commit()
                        print(f" NPI {npi_number} failed due to missing Org ID.\n")
                        continue

                    quickcap_test.switch_to_previous_window()
                    quickcap_test.click_add_new_location()
                    quickcap_test.enter_name1(name)
                    quickcap_test.enter_address2(address_line1 or "")
                    quickcap_test.enter_address_line2(address_line2 or "")
                    state_value = constants.STATE_DROPDOWN_MAP.get(state.strip(), "")
                    quickcap_test.select_state1(state_value)
                    quickcap_test.enter_zip1(zip_code or "")
                    quickcap_test.enter_city1(city or "")
                    quickcap_test.click_primary()
                    # quickcap_test.click_cancel1()
                    time.sleep(5)
                    quickcap_test.click_save1()
                    # ✅ Always close popup safely
                    if quickcap_test.driver.current_window_handle != main_window:
                        quickcap_test.driver.close()
                        quickcap_test.driver.switch_to.window(main_window)

                    # quickcap_test.switch_to_new_window1()
                    db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update(
                        {"status": 2}, synchronize_session=False
                    )
                    db.query(NPIAddress).filter(
                        NPIAddress.address_line1 == address_line1,
                        NPIAddress.npi == npi_number,
                        NPIAddress.update == 0
                    ).update({"update": 1}, synchronize_session=False)

                    db.commit()

                    print(f" NPI {npi_number} processed successfully.\n")

                    continue

            except Exception as e:
                print(e)
                break

            # quickcap_test.switch_to_new_window()
            selected_category = constants.CATEGORY_MAP.get(category.strip(), "") if category else ""
            quickcap_test.select_category_dropdown(selected_category)
            quickcap_test.select_provider_type_dropdown()
            # quickcap_test.select_primary_speciality_dropdown(network)
            quickcap_test.select_speciality(network)
            quickcap_test.click_quick_add_window_npi_button(npi_number)
            # quickcap_test.select_speciality1(network)
            quickcap_test.enter_provider_id(f"{npi_number}(A)")
            quickcap_test.enter_last_first_name(last_name or "", first_name or "")

            gender_map = {
                "Male": "M - Male", "M": "M - Male",
                "Female": "F - Female", "F": "F - Female"
            }
            selected_gender = gender_map.get(gender.strip(), "") if gender else ""
            quickcap_test.select_gender(selected_gender)

            full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime("%m/%d/%Y")
            quickcap_test.enter_contract_from_date(full_date)
            quickcap_test.select_contract_type("PENDING")
            quickcap_test.select_payment_type("FEE FOR SERVICE")
            quickcap_test.select_account("0000-000 DEFAULT")
            quickcap_test.click_organization()
            quickcap_test.switch_to_new_window1()
            quickcap_test.enter_npi_org(group_npi)
            quickcap_test.click_search_npi()
            success  = quickcap_test.click_org_id(npi_number, address_line1)
            if not success:
                # Org ID not found → update failure status here
                db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update({"status": 5})
                db.query(NPIAddress).filter(
                    NPIAddress.address_line1 == address_line1,
                    NPIAddress.npi == npi_number
                ).update({"update": 3})
                db.commit()
                print(f"NPI {npi_number} failed due to missing Org ID.\n")
                continue

            quickcap_test.switch_to_previous_window()
            # quickcap_test.select_org_from_popup("TEST ORG NAME")
            # quickcap_test.driver.close()
            # quickcap_test.switch_to_previous_window()
            # org_name = quickcap_test.get_org_name()
            quickcap_test.select_practice_type("GRP - GROUP")
            quickcap_test.enter_name(name)
            quickcap_test.enter_address1(address_line1 or "")
            quickcap_test.enter_address_line_2(address_line2 or "")
            state_value = constants.STATE_DROPDOWN_MAP.get(state.strip(), "")
            quickcap_test.select_state(state_value)
            quickcap_test.enter_city(city or "")
            quickcap_test.enter_zip(zip_code or "")
            quickcap_test.select_contract_template (company_name)
            time.sleep(5)
            quickcap_test.click_save()
            time.sleep(5)
            quickcap_test.accept_alert()
            time.sleep(5)
            quickcap_test.dismiss_alert()
            time.sleep(5)

            # time.sleep(3)
            quickcap_test.driver.close()
            quickcap_test.switch_to_new_window1()
            quickcap_test.switch_back_to_main()
            # quickcap_test.cancel_button_click_quick_add()
            # quickcap_test.handle_confirmation_popup("OK")
            #
            # # Handle second confirmation popup
            # quickcap_test.handle_confirmation_popup("OK")
            #
            # quickcap_test.switch_to_new_window1()
            db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update(
                {"status": 2}, synchronize_session=False
            )
            db.query(NPIAddress).filter(
                NPIAddress.address_line1 == address_line1,
                NPIAddress.npi == npi_number,
                NPIAddress.update == 0
            ).update({"update": 1}, synchronize_session=False)

            db.commit()

            print(f" NPI {npi_number} processed successfully.\n")
            continue

        quickcap_test.driver_close()

    except Exception as e:
        print(f"Critical error in test_qc: {e}")

    finally:
        db.close()


@pytest.mark.order(4)
@allure.feature("Monday Status Update")
@allure.story("Updating Monday.com status after QC processing")
def test_monday_status(monday_status_test):
    monday_status_test.login("autoprocess@pns-mgmt.com", "@VEnger200@@@@")
    monday_status_test.click_welcome_letter_qc()

    db: Session = SessionLocal()
    try:
        npi_records = db.query(PRSiteData).filter(PRSiteData.status.in_([2, 5])).all()

        if not npi_records:
            print("No NPI records with status = 2 or 5.")
            return

        first_iteration = True

        for record in npi_records:
            try:
                if first_iteration:
                    monday_status_test.click_search_button()
                    first_iteration = False

                monday_status_test.enter_npi_button(record.npi_number)
                time.sleep(2)

                if record.status == 2:
                    monday_status_test.click_not_started()
                    monday_status_test.click_done_button()
                    time.sleep(2)
                    monday_status_test.click_cross_button()
                    time.sleep(2)

                    record.status = 3
                    db.commit()
                    print(f"✅ NPI {record.npi_number} processed as Done.")

                elif record.status == 5:
                    monday_status_test.click_not_started()
                    monday_status_test.click_roadblock_button()
                    time.sleep(2)
                    monday_status_test.click_cross_button()
                    time.sleep(2)

                    record.status = 6
                    db.commit()
                    print(f" NPI {record.npi_number} marked as Roadblock.")

            except Exception as e:
                print(f" Error processing NPI {record.npi_number}: {str(e)}")

        monday_status_test.driver.close()

    finally:
        db.close()

# def test_company_change(quickcap_test_case):#
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


