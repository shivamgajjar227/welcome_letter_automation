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

    with allure.step("Connecting to database"):
        db: Session = SessionLocal()
        allure.attach("Database connection", "Connected successfully", allure.attachment_type.TEXT)

    try:
        with allure.step("Inserting NPI data into database"):
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
                allure.attach(f"Inserted NPI: {entry.get('npi_number')}",
                              f"Details: {entry}",
                              allure.attachment_type.TEXT)

        with allure.step("Committing database changes"):
            db.commit()
            allure.attach("Database commit", "All changes committed successfully", allure.attachment_type.TEXT)
            print("All NPIs inserted into pr_site_data table.")

    except Exception as e:
        with allure.step("Database operation failed - rolling back"):
            db.rollback()
            allure.attach("Database error", f"Error: {str(e)}", attachment_type=allure.attachment_type.TEXT)
            print("Error inserting data:", e)
            raise

    finally:
        with allure.step("Closing database connection"):
            db.close()
            allure.attach("Database connection", "Connection closed", allure.attachment_type.TEXT)

@pytest.mark.order(2)
@allure.feature("PR Site Data Grabbing")
@allure.story("Taking NPI Details From PR Site")
def test_pr_site(pr_sites_test):
    db = SessionLocal()
    try:
        with allure.step("Fetching NPI records with status 0 from DB"):
            npi_records = db.query(PRSiteData).filter(PRSiteData.status == 0).all()
            allure.attach(str([r.npi_number for r in npi_records]), "Fetched NPI Records")
            print("📄 Found NPI records with status 0:", [r.npi_number for r in npi_records])

        for record in npi_records:
            with allure.step(f"Processing NPI: {record.npi_number}"):
                pr_sites_test.hover_over_update_menuu()

                with allure.step("Entering NPI in Update Menu Search"):
                    npi = str(record.npi_number)
                    pr_sites_test.enter_npi_search(npi)
                    pr_sites_test.click_search_npi()
                    # time.sleep(3)

                with allure.step("Fetching Individual NPI Details"):
                    last_name = pr_sites_test.get_last_name()
                    first_name = pr_sites_test.get_first_name()
                    gender = pr_sites_test.get_gender()
                    npi_number = pr_sites_test.get_npi_number()
                    network = pr_sites_test.get_network()
                    city = pr_sites_test.get_city()
                    state = pr_sites_test.get_state()
                    zip_code = pr_sites_test.get_zip_code()
                    category = pr_sites_test.get_category()
                    speciality = pr_sites_test.get_speciality()
                    taxnonomy_code = pr_sites_test.get_taxonomy_code()

                    allure.attach(
                        f"""
                        Last Name: {last_name}
                        First Name: {first_name}
                        Gender: {gender}
                        NPI Number: {npi_number}
                        Network: {network}
                        City: {city}
                        State: {state}
                        Zip: {zip_code}
                        Category: {category}
                        Speciality: {speciality}
                        Taxonomy: {taxnonomy_code}
                        """,
                        f"Fetched NPI Data for {npi}"
                    )

                with allure.step("Fetching Group NPI and Group Name from Practice Menu"):
                    pr_sites_test.hover_over_practice_menu()
                    npi = str(record.npi_number)
                    pr_sites_test.enter_npi_search(npi)
                    pr_sites_test.click_search_npi()
                    # time.sleep(15)
                    group_npi = pr_sites_test.get_group_npi()
                    group_name = pr_sites_test.get_group_name()
                    # pr_sites_test.select_click_for_tax_id()
                    # tax_id = pr_sites_test.get_tax_id()
                    pr_sites_test.get_ind_npi_list_with_grp_npi_locations(record, group_npi)
                    allure.attach(
                        f"Group NPI: {group_npi}, Group Name: {group_name}",
                        f"Group Details for {npi}"
                    )
                    with allure.step("Cleaning and Preparing Data"):
                        cleaned_zip_code = zip_code.replace("-", "") if zip_code else None
                        allure.attach(f"Cleaned Zip: {cleaned_zip_code}", f"Data Cleaning for {npi}")
                        # cleaned_tax_id = tax_id.replace("-", "") if zip_code else None

            # print("✅ Updating:", npi)
            # print("Last Name:", last_name)
            # print("First Name:", first_name)
            # print("Gender:", gender)
            # print("network:", network)
            # print("City:", city)
            # print("State:", state)
            # print("Zip Code:", cleaned_zip_code)
            # print("Category:", category)
            # print("Speciality:", speciality)
            # print("taxonomy_code:", taxnonomy_code)
            # # print("Group NPI:", group_npi)
            # # print("Tax ID:", cleaned_tax_id)
            #
            # # npi_number = group_npi.split('-')[-1].strip()

                    with allure.step("Updating Database Record"):
                        record.last_name = last_name.upper()
                        record.first_name = first_name.upper()
                        record.gender = gender
                        record.network = network
                        record.city = city
                        record.state = state
                        record.zip_code = cleaned_zip_code
                        record.category = category
                        record.speciality = speciality
                        record.taxonomy_code = taxnonomy_code
                        record.status = 1

                        db.commit()
                        allure.attach("Record updated successfully", f"DB Commit for {npi}")
                        print("✅ Updated record:", npi)

    except Exception as e:
        db.rollback()
        allure.attach(str(e), "Error in test_pr_site")
        print(" Error in test_pr_site:", e)
        pytest.fail(f"Test failed due to error: {e}")

    finally:
        db.close()
        allure.attach("DB connection closed", "Database Cleanup")

@pytest.mark.order(3)
@allure.feature("QC Data Updating")
@allure.story("Updating data on QC for valid NPIs")
def test_qc(quickcap_test):
    main_window = quickcap_test.driver.current_window_handle
    db = SessionLocal()

    try:
        with allure.step("Clicking Company & Logging into QuickCap"):
            quickcap_test.click_company()

        quickcap_test.login("autoprocess@pns-mgmt.com", "Pns@072025")
        with allure.step("Fetching NPIs from Database with status=1 and update=0"):
            npi_records = db.query(PRSiteData.network,PRSiteData.health_plan,PRSiteData.npi_number,PRSiteData.last_name,PRSiteData.effective_date,PRSiteData.gender,PRSiteData.first_name,PRSiteData.category,PRSiteData.speciality
                                  , NPIAddress.state, NPIAddress.group_npi,NPIAddress.name,NPIAddress.address_line1,NPIAddress.address_line2,NPIAddress.zip_code,NPIAddress.city,PRSiteData.status,NPIAddress.update, PRSiteData.taxonomy_code).join(NPIAddress, PRSiteData.npi_number == NPIAddress.npi).filter(NPIAddress.update == 0,PRSiteData.status == 1).distinct(NPIAddress.zip_code).all()
            if not npi_records:
                allure.attach("No NPI records found with status=1", name="DB Result", attachment_type=allure.attachment_type.TEXT)
                print("No NPI records with status = 1.")
                return

            allure.attach(str(npi_records), name="Fetched NPIs", attachment_type=allure.attachment_type.TEXT)

        columns = [
            "network", "health_plan", "npi_number", "last_name", "effective_date",
            "gender","first_name", "category", "speciality",
            "state", "group_npi", "name", "address_line1","address_line2", "zip_code", "city", "status", "update","taxonomy_code"
        ]

        current_company = None

        for row in npi_records:
            record = dict(zip(columns, row))

            with allure.step(f"Processing NPI {record['npi_number']} for plan {record['health_plan']}"):
                network = safe_str(record["network"])
                health_plan = safe_str(record["health_plan"])
                npi_number = str(record["npi_number"] or "")
                last_name = safe_str(record["last_name"])
                effective_date = record["effective_date"]  # keep raw (date type)
                gender = safe_str(record["gender"])
                first_name = safe_str(record["first_name"])
                category = safe_str(record["category"])
                speciality = safe_str(record["speciality"])
                state = safe_str(record["state"])
                group_npi = str(record["group_npi"] or "")
                name = safe_str(record["name"])
                address_line1 = safe_str(record["address_line1"])
                address_line2 = safe_str(record["address_line2"])
                zip_code = str(record["zip_code"] or "")
                city = safe_str(record["city"])
                status = safe_str(record["status"])
                update = safe_str(record["update"])
                taxonomy_code = safe_str(record["taxonomy_code"])

                allure.attach(str(record), name=f"Record for {npi_number}", attachment_type=allure.attachment_type.TEXT)
                print(f"\n Processing NPI: {npi_number} | Health Plan: {health_plan} | Network: {network}")

                network = (network or "").strip().lower()
                health_plan = (health_plan or "").strip().lower()

                company_name = constants.COMPANY_MAP.get(network, {}).get(health_plan)
                if not company_name:
                    with allure.step(f"Skipping NPI {npi_number}: No company mapping found"):
                        allure.attach(f"Network: {network}, Health Plan: {health_plan}", name="Mapping Missing", attachment_type=allure.attachment_type.TEXT)
                        print(
                            f"Could not map company for network '{network}' and health plan '{health_plan}', skipping.")
                        continue

                with allure.step(f"Mapped Company {company_name}"):
                    allure.attach(company_name, name="Company Mapped", attachment_type=allure.attachment_type.TEXT)
                    print(f"Mapped Company: {company_name}")

            if current_company and current_company.lower() == company_name.lower():
                with allure.step(f"Company {company_name} already logged in, skipping re-login"):
                    print(f"✅ Company '{company_name}' already logged in — skipping change.")
                try:
                    with allure.step(f"Searching for NPI {npi_number}"):
                        if quickcap_test.check_npi_search_field():
                            quickcap_test.enter_npi(npi_number)
                            quickcap_test.click_search_button()
                            # time.sleep(5)
                        else:
                            quickcap_test.ensure_credentialing_tab()
                            quickcap_test.choose_credentialing_tab()
                            quickcap_test.choose_practitioner_data()
                            quickcap_test.enter_npi(npi_number)
                            quickcap_test.click_search_button()
                            # time.sleep(5)
                        allure.attach(f"NPI {npi_number} searched", "NPI Search", allure.attachment_type.TEXT)



                except Exception as e:
                    with allure.step("Search Error"):
                        allure.attach(str(e), "Error", allure.attachment_type.TEXT)
                        print(e)
                try:
                    # Wait for either "No data found" OR at least one table row
                    # WebDriverWait(quickcap_test.driver, 5).until(
                    #     lambda d: "No data found" in d.page_source or
                    #               len(d.find_elements(By.XPATH, "//table//tr[td]")) > 0
                    # )
                    # check_no_data_found = quickcap_test.check_no_data_found_text()
                    with allure.step(f"Handling Quick Add / Edit for {npi_number}"):
                        if not quickcap_test.is_edit_button_available():
                            # time.sleep(3)
                            quickcap_test.click_quick_add_button()
                            quickcap_test.switch_to_new_window1()
                            allure.attach("Quick Add invoked", "QuickAdd", allure.attachment_type.TEXT)
                        else:
                            # time.sleep(5)
                            quickcap_test.click_edit_button()
                            quickcap_test.switch_to_new_window1()

                            with allure.step("Provider setup"):
                                quickcap_test.click_provider_button()
                                provider_id = quickcap_test.provider_table_rows()
                                quickcap_test.click_add_provider()
                                quickcap_test.switch_to_new_window1()
                                quickcap_test.enter_provider_letter(provider_id)
                                quickcap_test.enter_last_name(last_name or "")
                                quickcap_test.enter_first_name(first_name or "")
                                full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                                    "%m/%d/%Y")
                                quickcap_test.enter_effective_date(full_date)
                                quickcap_test.select_contract_type1("CONTRACT FEE FOR SERVICE")
                                quickcap_test.select_speciality1(network)
                                quickcap_test.select_payment_type("FEE FOR SERVICE")
                                quickcap_test.enter_contract_from_date(full_date)
                                quickcap_test.select_provider_type_dropdown1(category, network, speciality)
                                quickcap_test.select_account1("0000-000 DEFAULT")
                                quickcap_test.select_template1(company_name)

                            with allure.step("Organization linking"):
                                quickcap_test.click_organization()
                                quickcap_test.switch_to_new_window1()
                                quickcap_test.enter_npi_org(group_npi)
                                quickcap_test.click_search_npi()
                                success = quickcap_test.click_org_id(npi_number,address_line1)
                                if not success:
                                    with allure.step("Org ID not found → marking failure in DB"):
                                        db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update({"status": 5})
                                        db.query(NPIAddress).filter(
                                            NPIAddress.address_line1 == address_line1,
                                            NPIAddress.npi == npi_number
                                        ).update({"update": 3})
                                        db.commit()
                                        allure.attach(
                                            f"NPI {npi_number} failed due to missing Org ID.",
                                            "Org Failure", allure.attachment_type.TEXT
                                        )
                                        print(f"NPI {npi_number} failed due to missing Org ID.\n")
                                        continue

                            with allure.step("Location entry"):
                                quickcap_test.switch_to_new_window1()
                                quickcap_test.click_add_new_location()

                            with allure.step(f"Enter Name: {name}"):
                                quickcap_test.enter_name1(name)

                            with allure.step(f"Enter Address Line1 : {address_line1}"):
                                quickcap_test.enter_address2(address_line1 or "")

                            with allure.step(f"Enter Address Line2 : {address_line2}"):
                                quickcap_test.enter_address_line2(address_line2 or "")

                                quickcap_test.select_state1("FL - FLORIDA")

                            with allure.step(f"Enter Zip Code: {zip_code}"):
                                quickcap_test.enter_zip1(zip_code)

                            with allure.step(f"Enter City: {city}"):
                                quickcap_test.enter_city1(city or "")

                            with allure.step("Click Primary"):
                                quickcap_test.click_primary()
                                # quickcap_test.click_cancel1()
                                # time.sleep(5)

                            with allure.step("Click Save"):
                                quickcap_test.click_save1()

                            with allure.step("Closing popup safely if exists"):
                                if quickcap_test.driver.current_window_handle != main_window:
                                    quickcap_test.driver.close()
                                    quickcap_test.driver.switch_to.window(main_window)

                            with allure.step("Healthplan entry"):
                                quickcap_test.enter_npi(npi_number)
                                quickcap_test.click_search_button()
                                quickcap_test.click_edit_button()
                                # time.sleep(3)
                                quickcap_test.switch_to_new_window()
                                quickcap_test.click_provider_button()
                                quickcap_test.click_edit_for_healthplan(provider_id)
                                quickcap_test.click_healthplan_panel()

                                quickcap_test.switch_to_new_window1()
                                full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                                    "%m/%d/%Y")
                                quickcap_test.enter_membership_date(full_date or "")
                                quickcap_test.click_plus_button()
                                quickcap_test.click_save_healthplan()
                                quickcap_test.driver.close()

                            with allure.step("Taxonomy entry"):
                                quickcap_test.switch_to_new_window()
                                quickcap_test.click_other_ids()
                                quickcap_test.click_add_plus()
                                quickcap_test.select_taxonomy("TAXONOMY - TAXONOMY")
                                quickcap_test.click_provider_id(provider_id)
                                quickcap_test.enter_taxonomy_code(taxonomy_code or "")
                                quickcap_test.click_save_taxonomy()

                            with allure.step("Finalizing & Updating DB"):
                                if quickcap_test.driver.current_window_handle != main_window:
                                    quickcap_test.driver.close()
                                    quickcap_test.driver.switch_to.window(main_window)

                                db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update(
                                    {"status": 2}, synchronize_session=False
                                )
                                db.query(NPIAddress).filter(
                                    NPIAddress.address_line1 == address_line1,
                                    NPIAddress.npi == npi_number,
                                    NPIAddress.update == 0
                                ).update({"update": 1}, synchronize_session=False)

                                db.commit()
                                allure.attach(
                                    f"NPI {npi_number} processed successfully",
                                    "DB Update", allure.attachment_type.TEXT
                                )
                                print(f" NPI {npi_number} processed successfully.\n")
                                continue

                except TimeoutException:
                    with allure.step("Timeout Error"):
                        allure.attach("Timed out waiting for search results", "Timeout",
                                      allure.attachment_type.TEXT)
                        print("Timed out waiting for search results.")

                # quickcap_test.click_quick_add_button()
                # quickcap_test.switch_to_new_window()
                with allure.step(f"Selecting category for NPI {npi_number}"):
                    selected_category = constants.CATEGORY_MAP.get(category.strip(), "") if category else ""
                    quickcap_test.select_category_dropdown(selected_category)

                with allure.step("Selecting provider type"):
                    quickcap_test.select_provider_type_dropdown(category, network, speciality)

                with allure.step("Selecting primary speciality"):
                    quickcap_test.select_speciality(network)

                with allure.step(f"Click Quick Add NPI button for {npi_number}"):
                    quickcap_test.click_quick_add_window_npi_button(npi_number)
                # quickcap_test.select_speciality1(network)
                with allure.step(f"Entering provider ID(A) and names: {last_name}, {first_name}"):
                    quickcap_test.enter_provider_id(f"{npi_number}(A)")
                    quickcap_test.enter_last_first_name(last_name or "", first_name or "")

                with allure.step(f"Selecting gender {gender}"):
                    gender_map = {
                        "Male": "M - Male", "M": "M - Male",
                        "Female": "F - Female", "F": "F - Female"
                    }
                    selected_gender = gender_map.get(gender.strip(), "") if gender else ""
                    quickcap_test.select_gender(selected_gender)

                with allure.step("Entering contract details"):
                    full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime("%m/%d/%Y")
                    quickcap_test.enter_contract_from_date(full_date)
                    quickcap_test.select_contract_type("CONTRACT FEE FOR SERVICE")
                    quickcap_test.select_payment_type("FEE FOR SERVICE")
                    quickcap_test.select_account("0000-000 DEFAULT")

                with allure.step("Linking NPI to Organization"):
                    quickcap_test.click_organization()
                    quickcap_test.switch_to_new_window1()
                    quickcap_test.enter_npi_org(group_npi)
                    quickcap_test.click_search_npi()
                    # time.sleep(3)
                    success = quickcap_test.click_org_id(npi_number, address_line1)  # Need to add WebDriver Wait here inside the pages
                    if not success:
                        with allure.step("Org ID not found → marking failure in DB"):
                            db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update({"status": 5})
                            db.query(NPIAddress).filter(
                                NPIAddress.address_line1 == address_line1,
                                NPIAddress.npi == npi_number
                            ).update({"update": 3})
                            db.commit()
                            allure.attach(f"NPI {npi_number} failed due to missing Org ID.", name="Org ID Failure",
                                          attachment_type=allure.attachment_type.TEXT)
                            continue

                with allure.step("Switch back to QuickCap main window"):
                    quickcap_test.switch_to_previous_window()
                    # quickcap_test.select_org_from_popup("TEST ORG NAME")
                    # quickcap_test.driver.close()
                    # quickcap_test.switch_to_previous_window()
                    # org_name = quickcap_test.get_org_name()

                with allure.step("Entering practice and address details"):
                    quickcap_test.select_practice_type("GRP - GROUP")

                with allure.step(f"Enter Name: {name}"):
                    quickcap_test.enter_name(name)

                with allure.step(f"Enter Address Line1: {address_line1}"):
                    quickcap_test.enter_address1(address_line1 or "")

                with allure.step(f"Enter Address Line2 : {address_line2}"):
                    quickcap_test.enter_address_line_2(address_line2 or "")

                state_value = constants.STATE_DROPDOWN_MAP.get(state.strip(), "")
                with allure.step(f"Enter State: {state_value}"):
                    quickcap_test.select_state(state_value)

                with allure.step(f"Enter City: {city}"):
                    quickcap_test.enter_city(city or "")

                with allure.step(f"Enter Zip Code: {zip_code}"):
                    quickcap_test.enter_zip(zip_code)

                with allure.step(f"Enter Contract Template"):
                    quickcap_test.select_contract_template(company_name)
                    # time.sleep(3)
                    quickcap_test.click_save()

                with allure.step("Closing popup safely if exists"):
                    if quickcap_test.driver.current_window_handle != main_window:
                        quickcap_test.driver.close()
                        quickcap_test.driver.switch_to.window(main_window)

                with allure.step("Searching and editing NPI record"):
                    quickcap_test.enter_npi(npi_number)
                    quickcap_test.click_search_button()
                    quickcap_test.click_edit_button()
                    # time.sleep(3)
                    quickcap_test.switch_to_new_window()
                    quickcap_test.click_provider_button()
                    quickcap_test.click_edit_for_healthplan_for_A()
                    quickcap_test.click_healthplan_panel()

                with allure.step("Adding Healthplan details"):
                    quickcap_test.switch_to_new_window1()
                    full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                        "%m/%d/%Y")
                    quickcap_test.enter_membership_date(full_date or "")
                    quickcap_test.click_plus_button()
                    quickcap_test.click_save_healthplan()
                    quickcap_test.driver.close()
                    quickcap_test.switch_to_new_window()

                with allure.step("Adding Taxonomy details"):
                    quickcap_test.click_other_ids()
                    quickcap_test.click_add_plus()
                    quickcap_test.select_taxonomy("TAXONOMY - TAXONOMY")
                    quickcap_test.click_provider_id_for_A()
                    quickcap_test.enter_taxonomy_code(taxonomy_code or "")
                    quickcap_test.click_save_taxonomy()

                with allure.step("Closing taxonomy popup if open"):
                    if quickcap_test.driver.current_window_handle != main_window:
                        quickcap_test.driver.close()
                        quickcap_test.driver.switch_to.window(main_window)

                # quickcap_test.switch_to_new_window1()
                with allure.step(f"Updating DB status for successful NPI {npi_number}"):
                    db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update(
                        {"status": 2}, synchronize_session=False
                    )
                    db.query(NPIAddress).filter(
                        NPIAddress.address_line1 == address_line1,
                        NPIAddress.npi == npi_number,
                        NPIAddress.update == 0
                    ).update({"update": 1}, synchronize_session=False)

                    db.commit()
                    allure.attach(f"NPI {npi_number} processed successfully.", name="QuickCap Success",
                                  attachment_type=allure.attachment_type.TEXT)
                    continue

            with allure.step("Storing main window handle"):
                quickcap_test.store_main_window()

            with allure.step(f"Switching company to {company_name}"):
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
                # time.sleep(5)

            with allure.step(f"Searching NPI {npi_number}"):
                try:
                    # quickcap_test.expand_menu_if_cigna(company_name="Cigna")

                    if quickcap_test.is_access_denied():
                        allure.attach("Access Denied page encountered. Navigating back...",
                                      name="Access Denied",
                                      attachment_type=allure.attachment_type.TEXT)
                        quickcap_test.driver.back()
                        # time.sleep(2)
                        # try again expanding menu
                        # quickcap_test.expand_menu_if_cigna(company_name="Cigna")
                    if quickcap_test.check_npi_search_field():
                        quickcap_test.enter_npi(npi_number)
                        quickcap_test.click_search_button()
                        # time.sleep(5)
                    else:
                        quickcap_test.ensure_credentialing_tab()
                        quickcap_test.choose_credentialing_tab()
                        quickcap_test.choose_practitioner_data()
                        # time.sleep(5)
                        quickcap_test.enter_npi(npi_number)
                        quickcap_test.click_search_button()
                        # time.sleep(5)
                except Exception as e:
                    allure.attach(str(e), name="Search Error", attachment_type=allure.attachment_type.TEXT)
                    raise

            with allure.step(f"Checking for Edit or Quick Add for {npi_number}"):
                try:
                    if not quickcap_test.is_edit_button_available():
                        # time.sleep(3)
                        quickcap_test.click_quick_add_button()
                        quickcap_test.switch_to_new_window1()
                        allure.attach("Quick Add invoked", "QuickAdd", allure.attachment_type.TEXT)
                    else:
                        quickcap_test.click_edit_button()
                        time.sleep(3)
                        quickcap_test.switch_to_new_window1()

                        with allure.step("Provider setup"):
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
                            quickcap_test.select_contract_type1("CONTRACT FEE FOR SERVICE")
                            quickcap_test.select_speciality1(network)
                            quickcap_test.select_payment_type("FEE FOR SERVICE")
                            quickcap_test.enter_contract_from_date(full_date)
                            quickcap_test.select_provider_type_dropdown1(category,network,speciality)
                            quickcap_test.select_account1("0000-000 DEFAULT")
                            quickcap_test.select_template1(company_name)

                        with allure.step("Organization linking"):
                            quickcap_test.click_organization()
                            quickcap_test.switch_to_new_window1()
                            quickcap_test.enter_npi_org(group_npi)
                            quickcap_test.click_search_npi()
                            success = quickcap_test.click_org_id(npi_number, address_line1)
                            if not success:
                                with allure.step("Org ID not found → marking failure in DB"):
                                    db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update(
                                        {"status": 5})
                                    db.query(NPIAddress).filter(
                                        NPIAddress.address_line1 == address_line1,
                                        NPIAddress.npi == npi_number
                                    ).update({"update": 3})
                                    db.commit()
                                    allure.attach(
                                        f"NPI {npi_number} failed due to missing Org ID.",
                                        "Org Failure", allure.attachment_type.TEXT
                                    )
                                    print(f"NPI {npi_number} failed due to missing Org ID.\n")
                                    continue

                        with allure.step("Location entry"):
                            quickcap_test.switch_to_previous_window()
                            quickcap_test.click_add_new_location()

                        with allure.step(f"Enter Name: {name}"):
                            quickcap_test.enter_name1(name)

                        with allure.step(f"Enter Address Line1: {address_line1}"):
                            quickcap_test.enter_address2(address_line1 or "")

                        with allure.step(f"Enter Address Line2: {address_line2}"):
                            quickcap_test.enter_address_line2(address_line2 or "")
                        state_value = constants.STATE_DROPDOWN_MAP.get(state.strip(), "")
                        with allure.step(f"Enter State: {state_value}"):

                            quickcap_test.select_state1(state_value)

                        with allure.step(f"Enter Zip Code: {zip_code}"):
                            quickcap_test.enter_zip1(zip_code or "")

                        with allure.step(f"Enter City: {city}"):
                            quickcap_test.enter_city1(city or "")

                        with allure.step("Select Primary"):
                            quickcap_test.click_primary()
                            # quickcap_test.click_cancel1()
                            # time.sleep(5)

                        with allure.step("Click Save"):
                            quickcap_test.click_save1()

                            # ✅ Always close popup safely
                            if quickcap_test.driver.current_window_handle != main_window:
                                quickcap_test.driver.close()
                                quickcap_test.driver.switch_to.window(main_window)

                        with allure.step(f"Editing NPI and adding Healthplan for {npi_number}"):
                            quickcap_test.enter_npi(npi_number)
                            quickcap_test.click_search_button()
                            quickcap_test.click_edit_button()
                            # time.sleep(3)
                            quickcap_test.switch_to_new_window()
                            quickcap_test.click_provider_button()
                            quickcap_test.click_edit_for_healthplan(provider_id)
                            quickcap_test.click_healthplan_panel()

                            quickcap_test.switch_to_new_window1()
                            full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                                "%m/%d/%Y")
                            quickcap_test.enter_membership_date(full_date or "")
                            quickcap_test.click_plus_button()
                            quickcap_test.click_save_healthplan()
                            quickcap_test.driver.close()

                        with allure.step("Adding Taxonomy"):
                            quickcap_test.switch_to_new_window()
                            quickcap_test.click_other_ids()
                            quickcap_test.click_add_plus()
                            quickcap_test.select_taxonomy("TAXONOMY - TAXONOMY")
                            quickcap_test.click_provider_id(provider_id)
                            quickcap_test.enter_taxonomy_code(taxonomy_code or "")
                            quickcap_test.click_save_taxonomy()

                            if quickcap_test.driver.current_window_handle != main_window:
                                quickcap_test.driver.close()
                                quickcap_test.driver.switch_to.window(main_window)

                        with allure.step("Updating DB status"):
                            db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update(
                                {"status": 2}, synchronize_session=False
                            )
                            db.query(NPIAddress).filter(
                                NPIAddress.address_line1 == address_line1,
                                NPIAddress.npi == npi_number,
                                NPIAddress.update == 0
                            ).update({"update": 1}, synchronize_session=False)

                            db.commit()
                            allure.attach(f"NPI {npi_number} processed successfully.", name="Success",
                                          attachment_type=allure.attachment_type.TEXT)
                            continue


                except Exception as e:
                    allure.attach(str(e), name="Pre-processing Error", attachment_type=allure.attachment_type.TEXT)
                    print(e)
                    break

            # quickcap_test.switch_to_new_window()
            with allure.step(f"Selecting category for NPI {npi_number}"):
                selected_category = constants.CATEGORY_MAP.get(category.strip(), "") if category else ""
                quickcap_test.select_category_dropdown(selected_category)

            with allure.step("Selecting provider type"):
                quickcap_test.select_provider_type_dropdown(category,network,speciality)
                # quickcap_test.select_primary_speciality_dropdown(network)

            with allure.step("Selecting primary speciality"):
                quickcap_test.select_speciality(network)

            with allure.step(f"Click Quick Add NPI button for {npi_number}"):
                quickcap_test.click_quick_add_window_npi_button(npi_number)
                # quickcap_test.select_speciality1(network)

            with allure.step(f"Entering provider ID(A) and names: {last_name}, {first_name}"):
                quickcap_test.enter_provider_id(f"{npi_number}(A)")
                quickcap_test.enter_last_first_name(last_name or "", first_name or "")

            with allure.step(f"Selecting gender {gender}"):
                gender_map = {
                    "Male": "M - Male", "M": "M - Male",
                    "Female": "F - Female", "F": "F - Female"
                }
                selected_gender = gender_map.get(gender.strip(), "") if gender else ""
                quickcap_test.select_gender(selected_gender)

            with allure.step("Entering contract details"):
                full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime("%m/%d/%Y")
                quickcap_test.enter_contract_from_date(full_date)
                quickcap_test.select_contract_type("CONTRACT FEE FOR SERVICE")
                quickcap_test.select_payment_type("FEE FOR SERVICE")
                quickcap_test.select_account("0000-000 DEFAULT")

            with allure.step("Linking NPI to Organization"):
                quickcap_test.click_organization()
                quickcap_test.switch_to_new_window1()
                quickcap_test.enter_npi_org(group_npi)
                quickcap_test.click_search_npi()
                success  = quickcap_test.click_org_id(npi_number, address_line1)
                if not success:
                    with allure.step("Org ID not found → marking failure in DB"):
                        db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update({"status": 5})
                        db.query(NPIAddress).filter(
                            NPIAddress.address_line1 == address_line1,
                            NPIAddress.npi == npi_number
                        ).update({"update": 3})
                        db.commit()
                        allure.attach(f"NPI {npi_number} failed due to missing Org ID.", name="Org ID Failure",
                                      attachment_type=allure.attachment_type.TEXT)
                        continue

            with allure.step("Switch back to QuickCap main window"):
                quickcap_test.switch_to_previous_window()
                # quickcap_test.select_org_from_popup("TEST ORG NAME")
                # quickcap_test.driver.close()
                # quickcap_test.switch_to_previous_window()
                # org_name = quickcap_test.get_org_name()

            with allure.step("Entering practice and address details"):
                quickcap_test.select_practice_type("GRP - GROUP")

            with allure.step(f"Enter Name: {name}"):
                quickcap_test.enter_name(name)


            with allure.step(f"Enter Address Line1: {address_line1}"):
                quickcap_test.enter_address1(address_line1 or "")

            with allure.step(f"Enter Address Line2: {address_line2}"):
                quickcap_test.enter_address_line_2(address_line2 or "")

            state_value = constants.STATE_DROPDOWN_MAP.get(state.strip(), "")
            with allure.step(f"Enter State: {state_value}"):
                quickcap_test.select_state(state_value)

            with allure.step(f"Enter City: {city}"):
                quickcap_test.enter_city(city or "")

            with allure.step(f"Enter Zip Code: {zip_code}"):
                quickcap_test.enter_zip(zip_code or "")

            with allure.step("Select Contract Type"):
                quickcap_test.select_contract_template (company_name)

            with allure.step("Saving contract form"):
                # time.sleep(5)
                quickcap_test.click_save()
                # time.sleep(5)
                quickcap_test.accept_alert()
                # time.sleep(5)
                quickcap_test.dismiss_alert()
                # time.sleep(5)
                allure.attach(f"NPI {npi_number} contract form saved successfully",
                              name="Contract Save",
                              attachment_type=allure.attachment_type.TEXT)

            # time.sleep(3)
            with allure.step("Closing form window and switching back to main"):
                quickcap_test.driver.close()
                quickcap_test.switch_to_new_window1()
                quickcap_test.switch_back_to_main()

            with allure.step("Re-opening provider details"):
                quickcap_test.enter_npi(npi_number)
                quickcap_test.click_search_button()
                quickcap_test.click_edit_button()
                # time.sleep(3)
                quickcap_test.switch_to_new_window()
                quickcap_test.click_provider_button()
                quickcap_test.click_edit_for_healthplan_for_A()
                quickcap_test.click_healthplan_panel()

            with allure.step("Adding membership and health plan details"):
                quickcap_test.switch_to_new_window1()
                full_date = datetime.strptime(effective_date.strip() + " 2025", "%b %d %Y").strftime(
                    "%m/%d/%Y")
                quickcap_test.enter_membership_date(full_date or "")
                quickcap_test.click_plus_button()
                quickcap_test.click_save_healthplan()
                quickcap_test.driver.close()
                allure.attach(f"Membership date {full_date} saved for NPI {npi_number}",
                              name="Membership Save",
                              attachment_type=allure.attachment_type.TEXT)

            with allure.step("Adding taxonomy details"):
                quickcap_test.switch_to_new_window()
                quickcap_test.click_other_ids()
                quickcap_test.click_add_plus()
                quickcap_test.select_taxonomy("TAXONOMY - TAXONOMY")
                quickcap_test.click_provider_id_for_A()
                quickcap_test.enter_taxonomy_code(taxonomy_code or "")
                quickcap_test.click_save_taxonomy()
                allure.attach(f"Taxonomy {taxonomy_code} saved for NPI {npi_number}",
                              name="Taxonomy Save",
                              attachment_type=allure.attachment_type.TEXT)

            with allure.step("Switching back to main window if needed"):
                if quickcap_test.driver.current_window_handle != main_window:
                        quickcap_test.driver.close()
                        quickcap_test.driver.switch_to.window(main_window)

            with allure.step("Final DB update for NPI"):
                db.query(PRSiteData).filter(PRSiteData.npi_number == npi_number).update(
                    {"status": 2}, synchronize_session=False
                )
                db.query(NPIAddress).filter(
                    NPIAddress.address_line1 == address_line1,
                    NPIAddress.npi == npi_number,
                    NPIAddress.update == 0
                ).update({"update": 1}, synchronize_session=False)

                db.commit()
                allure.attach(f"NPI {npi_number} processed successfully.",
                              name="Processing Success",
                              attachment_type=allure.attachment_type.TEXT)
                print(f"✅ NPI {npi_number} processed successfully.\n")
                continue

        quickcap_test.driver_close()

    except Exception as e:
        with allure.step("Critical error handling"):
            allure.attach(
                str(e),
                name="Exception Trace",
                attachment_type=allure.attachment_type.TEXT
            )
            print(f" Critical error in test_qc: {e}")

    finally:
        with allure.step("Closing DB session and driver"):
            db.close()
            quickcap_test.driver_close()
            allure.attach(
                "Database session closed and driver terminated.",
                name="Teardown",
                attachment_type=allure.attachment_type.TEXT
            )

@pytest.mark.order(4)
@allure.feature("Monday Status Update")
@allure.story("Updating Monday.com status after QC processing")
def test_monday_status(monday_status_test):

    with allure.step("Logging into Monday.com"):
        monday_status_test.login("autoprocess@pns-mgmt.com", "@VEnger200@@@@")

    with allure.step("Navigating to Welcome Letter QC"):
        monday_status_test.click_welcome_letter_qc()

    db: Session = SessionLocal()
    try:
        with allure.step("Fetching NPI records with status 2 or 5 from DB"):
            npi_records = db.query(PRSiteData).filter(PRSiteData.status.in_([2, 5])).all()

        if not npi_records:
            allure.attach("No NPI records with status = 2 or 5.",
                          name="No Records Found",
                          attachment_type=allure.attachment_type.TEXT)
            return

        first_iteration = True

        for record in npi_records:
            with allure.step(f"Processing NPI: {record.npi_number} (Status: {record.status})"):
                try:
                    # if first_iteration:
                    #     with allure.step("Clicking search button for first iteration"):
                    #         monday_status_test.click_search_button()
                    #         first_iteration = False
                    #
                    # monday_status_test.enter_npi_button(record.npi_number)
                    # time.sleep(2)

                    if record.status == 2 or record.status == 5:
                        if first_iteration:
                            with allure.step("Clicking search button for first iteration"):
                                monday_status_test.click_search_button()
                            first_iteration = False

                        monday_status_test.enter_npi_button(record.npi_number)
                        # time.sleep(2)

                        monday_health_plans = monday_status_test.get_all_health_plans_from_ui()

                        health_plan_match = False
                        db_health_plan_clean = record.health_plan.strip().lower() if record.health_plan else ""

                        if monday_health_plans and db_health_plan_clean:
                            for monday_health_plan in monday_health_plans:
                                monday_health_plan_clean = monday_health_plan.strip().lower()
                                # Handle truncated names and partial matches
                                if (monday_health_plan_clean == db_health_plan_clean or
                                        db_health_plan_clean.startswith(
                                            monday_health_plan_clean.replace('...', '').replace('…', '').strip()) or
                                        monday_health_plan_clean.startswith(db_health_plan_clean.split()[0].lower())):
                                    health_plan_match = True
                                    matched_health_plan = monday_health_plan
                                    break

                        if health_plan_match:
                            with allure.step(
                                    f"Health plan match found: {matched_health_plan} - Processing NPI {record.npi_number}"):

                                if record.status == 2:
                                    with allure.step("Marking NPI as Done"):
                                        monday_status_test.click_not_started_for_matching_health_plans(db_health_plan=record.health_plan)
                                        monday_status_test.click_review_button()
                                        # time.sleep(2)
                                        monday_status_test.click_cross_button()
                                        # time.sleep(2)

                                        record.status = 3
                                        db.commit()
                                        allure.attach(f"NPI {record.npi_number} processed as Done.",
                                                      name="Processing Success",
                                                      attachment_type=allure.attachment_type.TEXT)
                                        print(f" NPI {record.npi_number} processed as Done.")

                                elif record.status == 5:
                                    with allure.step("Marking NPI as Roadblock"):
                                        npi_address = db.query(NPIAddress).filter(
                                            NPIAddress.npi == record.npi_number).first()

                                        if npi_address and npi_address.remarks:
                                            remarks_text = npi_address.remarks
                                            print(f" Found remarks in DB for NPI {record.npi_number}: {remarks_text}")
                                        else:
                                            remarks_text = "Organisation Data Missing"
                                            print(
                                                f"⚠No remarks found in DB for NPI {record.npi_number}, using default")

                                        remarks_added = monday_status_test.process_rows_and_enter_remarks(
                                            db_health_plan=record.health_plan,
                                            db_effective_date=record.effective_date,
                                            remarks_text=remarks_text
                                        )

                                        if remarks_added:
                                            print(f" Remarks added to matching rows for NPI {record.npi_number}")
                                            # Continue with Roadblock process
                                            # monday_status_test.click_not_started()
                                            monday_status_test.click_not_started_for_matching_health_plans(db_health_plan=record.health_plan)
                                            monday_status_test.click_roadblock_button()
                                            # time.sleep(2)
                                            monday_status_test.click_cross_button()
                                            # time.sleep(2)
                                            record.status = 6
                                            db.commit()
                                        else:
                                            print(f" No matching rows found for NPI {record.npi_number}")
                                else:
                                    print(f"No remarks found in DB for NPI {record.npi_number}")
                        else:
                            if monday_health_plans:
                                monday_plans_str = ", ".join(monday_health_plans)
                            else:
                                monday_plans_str = "No health plans found in UI"

                            allure.attach(
                                f"No health plan match for NPI {record.npi_number}. DB: {record.health_plan}, Monday.com: {monday_plans_str}",
                                name="Health Plan Mismatch",
                                attachment_type=allure.attachment_type.TEXT)
                            print(
                                f"Skipping NPI {record.npi_number} - Health plan mismatch. DB: {record.health_plan}, Monday.com: {monday_plans_str}")
                            continue

                except Exception as e:
                    allure.attach(f"Error processing NPI {record.npi_number}: {str(e)}",
                                  name="Processing Error",
                                  attachment_type=allure.attachment_type.TEXT)
                    print(f" Error processing NPI {record.npi_number}: {str(e)}")

        with allure.step("Closing Monday.com window"):
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


