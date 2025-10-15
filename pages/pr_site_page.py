import time

from selenium.common import TimeoutException, StaleElementReferenceException ,  NoSuchElementException
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from models import PRSiteData
from datetime import datetime
from db.session import SessionLocal
from api import pr_site_data
from models import NPIAddress
from pages.base_page import BasePage
from core import loggin_utils
import logging

log_name =  "PRSitePage"
logger_setup = loggin_utils.setup_logger(log_name, level='INFO')
logger = logging.getLogger(log_name)

class PRSitePage(BasePage):

    provider_menu = (By.CSS_SELECTOR, "a[href='#s1']")
    update_menu = (By.XPATH, "//li[@id='ctl00_li_ProvUpdate']")
    npi_search = (By.CSS_SELECTOR, "#ctl00_MainContent_uCSearchProvider_txtSearchProvider")
    npi_search_dropdown = (By.CSS_SELECTOR, "#ctl00_MainContent_uCSearchProvider_autocomplete_providers_completionListElem")
    search_button = (By.CSS_SELECTOR, "#ctl00_MainContent_uCSearchProvider_btn_Search")
    project_type = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Personal_Info_lblProjectType")
    individual_npi = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Personal_Info_lblIndividualNPI")
    last_name = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Personal_Info_lblLName")
    first_name = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Personal_Info_lblFName")
    gender = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Personal_Info_lblGender")
    npi_number = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Personal_Info_lblIndividualNPI")
    city = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Medical_Info_lblCity")
    state = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Medical_Info_lblState")
    zip_code = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Medical_Info_lblZipCode")
    category = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Medical_Info_lblDegree")
    speciality = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Medical_Info_lblSpecialties")
    network = (By.CSS_SELECTOR, "#ctl00_MainContent_uCSearchProvider_fm_ProviderMainInfo_lblNetwork")
    click_for_npi = (By.CSS_SELECTOR, "#ctl00_MainContent_GvProvPractice_ctl02_LnkGroupName")
    # group_npi = (By.CSS_SELECTOR, "#ctl00_MainContent_fmGroupBillingInfo_lblGroupNPI")
    click_for_tax_id = (By.XPATH, "//a[@id='ctl00_MainContent_GvProvPractice_ctl02_LnkGroupName']")
    tax_id = (By.XPATH, "(//span[@id='ctl00_MainContent_fmGroupBillingInfo_lblGroupTIN'])[1]")
    texonomy_code = (By.XPATH, "//span[@id='ctl00_MainContent_fm_Prov_Medical_Info_lblTaxonomyGroup']")
    inv_npi_list_table = (By.XPATH, "//div[@id='ctl00_MainContent_pnlGvListPractice']/div/table/tbody/tr")
    npi_list_expansion_arrow = (By.XPATH, "//a[contains(@id,'LnkExpandPract')]")

    def hover_over_provider_menu(self):
        provide_webelement = self.driver.find_element(*self.provider_menu)
        actions = ActionChains(self.driver)
        actions.move_to_element(provide_webelement).perform()
        time.sleep(2)

        sub_menu = self.driver.find_element(*self.update_menu)
        sub_menu.click()

    def hover_over_update_menu(self):
        provide_webelement = self.driver.find_element(*self.provider_menu)
        actions = ActionChains(self.driver)
        actions.move_to_element(provide_webelement).perform()
        time.sleep(5)
        sub_menu = self.driver.find_element(By.XPATH, "//a[normalize-space()='Update']")
        time.sleep(2)
        sub_menu.click()

    def hover_over_update_menuu(self, max_retries=3):
        """Hovers over provider menu and clicks Update with retry logic"""
        logger.info("Inside of hover and over update menu")
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Attempt {attempt} of {max_retries} to hover and click Update")

                # Wait for and hover over provider menu
                provider_element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(self.provider_menu)
                )
                ActionChains(self.driver).move_to_element(provider_element).perform()

                # Wait for and click Update submenu
                update_element = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Update']"))
                )
                update_element.click()
                return True

                logger.info("Out from hover over update menu")

            except Exception as e:
                print(f"Attempt {attempt} failed: {str(e)}")
                if attempt == max_retries:
                    print("Max retries reached, giving up")
                    return False

                # Recovery actions
                print("Refreshing page and retrying...")
                self.driver.refresh()
                time.sleep(2)

    def enter_npi_search(self, value):
        logger.info(f"Inside Enter NPI Search")
        try:
            self.enter_text(self.npi_search, value)
            time.sleep(5)
            dropdown_options = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located(self.npi_search_dropdown)
            )
            for options in dropdown_options:
                if value in options.text:
                    options.click()
                    break
            clickable_option = WebDriverWait(self.driver,10).until(EC.element_to_be_clickable(self.search_button))
            clickable_option.click()
            logger.info(f"Out from NPI Search")
        except Exception as e:
            print(f" Unexpected error while enter npi search: {type(e).__name__}")

    def click_search_npi(self):
        logger.info(f"Inside Click Search NPI")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.search_button)
            )
            element.click()
            time.sleep(10)
            print("Search button clicked successfully.")
            logger.info(f"Out from Search NPI")
        except Exception as e:
            print(f" Unexpected error while clicking search npi: {type(e).__name__}")

    def get_project_type(self):
        return self.driver.find_element(*self.project_type).text.strip()

    def get_individual_npi(self):
        return self.driver.find_element(*self.individual_npi).text.strip()

    def get_last_name(self):
        logger.info(f"Inside get Last Name")
        try:
            wait = WebDriverWait(self.driver, 20)

            element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Personal_Info_lblLName"))
            )
            return element.text.strip()
            logger.info(f"Out from get Last Name")
        except Exception as e:
            print(" Could not find Last Name:", e)
            self.driver.save_screenshot("lname_error.png")
            return None

    def get_first_name(self):
        logger.info(f"Inside get First Name")
        try:
            element = self.driver.find_element(*self.first_name)
            return element.text.strip()
            logger.info(f"Out from get First Name")
        except NoSuchElementException:
            print("First name element not found.")
            return None

    def get_gender(self):
        logger.info(f"Inside get Gender")
        try:
            return self.driver.find_element(*self.gender).text.strip()
            logger.info(f"Out from get Gender")
        except NoSuchElementException:
            print("Gender element not found.")
            return None

    def get_npi_number(self):
        try:
            return self.driver.find_element(*self.npi_number).text.strip()
        except NoSuchElementException:
            print("NPI Number element not found.")
            return None

    def get_city(self):
        logger.info(f"Inside get City")
        try:
            return self.driver.find_element(*self.city).text.strip()
            logger.info(f"Out from get City")
        except NoSuchElementException:
            print("City element not found.")
            return None

    def get_state(self):
        logger.info(f"Inside get State")
        try:
            return self.driver.find_element(*self.state).text.strip()
            logger.info(f"Out from get State")
        except NoSuchElementException:
            print("State element not found.")
            return None

    def get_zip_code(self):
        logger.info(f"Inside get Zip Code")
        try:
            return self.driver.find_element(*self.zip_code).text.strip()
            logger.info(f"Out from get Zip Code")
        except NoSuchElementException:
            print("Zip Code element not found.")
            return None

    def get_category(self):
        logger.info(f"Inside get Category")
        try:
            return self.driver.find_element(*self.category).text.strip()
            logger.info(f"Out from get Category")
        except NoSuchElementException:
            print("Category element not found.")
            return None

    def get_speciality(self):
        logger.info(f"Inside get Speciality")
        try:
            return self.driver.find_element(*self.speciality).text.strip()
            logger.info(f"Out from get Speciality")
        except NoSuchElementException:
            print("Speciality element not found.")
            return None

    def get_network(self):
        logger.info(f"Inside get Network")
        try:
            return self.driver.find_element(*self.network).text.strip()
            logger.info(f"Out from get Network")
        except NoSuchElementException:
            print("Network element not found.")
            return None

    def hover_over_practice_menu(self, retries: int = 3):
        logger.info("Inside Hover Over Practice Menu")
        attempt = 0
        while attempt < retries:
            try:
                # Hover over provider menu
                provide_webelement = WebDriverWait(self.driver, 10).until(
                    EC.visibility_of_element_located(self.provider_menu)
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", provide_webelement)
                ActionChains(self.driver).move_to_element(provide_webelement).perform()

                # Wait for submenu and click
                sub_menu = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@href='/ProvPractice.aspx']"))
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", sub_menu)
                sub_menu.click()

                logger.info("Out from Hover Over Practice Menu")
                return  # ✅ success, exit the function
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                attempt += 1
                time.sleep(2)  # small wait before retry

        raise Exception("Failed to hover and click practice menu after retries")

    def select_click_for_npi(self):
        self.click(self.click_for_npi)

    def get_group_npi(self):
        logger.info(f"Inside get Group NPI")
        try:
            element = WebDriverWait(self.driver, 15).until(
                EC.visibility_of_element_located(self.click_for_npi)
            )
            return element.text.strip()
            logger.info(f"Out from get Group NPI")
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Error getting group NPI: {e}")
            return None

    def get_group_name(self):
        logger.info(f"Inside get Group Name")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.click_for_npi)
            )
            return element.text.strip()
            logger.info(f"Out from get Group Name")
        except (TimeoutException, NoSuchElementException) as e:
            print(f"Error getting group Name: {e}")
            return None

    def get_name(self):
        element = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.click_for_npi)
        )
        return element.text.strip()

    def test_handle_multiple_tabs(self):
        driver = self.driver
        wait = WebDriverWait(driver, 20)
        main_window = driver.current_window_handle
        print(main_window)
        group_npi= ""
        try:
            # === STEP 1: Click Group Link with Stale Retry ===
            for attempt in range(2):
                try:
                    group_link = wait.until(EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, "#ctl00_MainContent_GvProvPractice_ctl02_LnkGroupName")
                    ))
                    group_link.click()
                    break  # Success, exit loop
                except StaleElementReferenceException:
                    print("Retrying due to stale element...")
                    time.sleep(1)
            else:
                raise Exception("Group link click failed after retries")

            # === STEP 2: Wait Until New Tabs Open ===
            wait.until(lambda d: len(d.window_handles) > 1)
            all_windows = driver.window_handles
            new_tabs = [win for win in all_windows if win != main_window]

            if len(new_tabs) >= 2:
                # === STEP 3: Switch to Last Tab ===
                driver.switch_to.window(new_tabs[-1])
                print("Switched to last tab. Title:", driver.title)

                # === STEP 4: Wait and Extract Data ===
                data_element = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "(//div[@class='col-md-3']/span[@class='lbl-data'])[1]")
                ))
                group_npi = data_element.text
                print("Extracted NPI:", data_element.text)

                # === STEP 5: Close All New Tabs ===
                for tab in new_tabs:
                    driver.switch_to.window(tab)
                    driver.close()

                # === STEP 6: Return to Main Window ===
                driver.switch_to.window(main_window)
                print("Returned to main window. Title:", driver.title)
                return group_npi

            else:
                print("Less than 2 new tabs opened. Found:", len(new_tabs))

        except TimeoutException as te:
            print("Timeout while waiting for element or tab:", te)
        except Exception as e:
            print("Error in test_handle_multiple_tabs:", e)
            driver.save_screenshot("error_tab_switch.png")
            raise

    def select_click_for_tax_id(self):
        self.click(self.click_for_tax_id)

    def get_tax_id(self):
        return self.driver.find_element(*self.tax_id).text.strip()

    def get_taxonomy_code(self):
        logger.info(f"Inside get Taxonomy Code")
        try:
            return self.driver.find_element(*self.texonomy_code).text.strip()
            logger.info(f"Out from get Taxonomy Code")
        except NoSuchElementException:
            print("Taxonomy Code element not found.")
            return None

    def get_ind_npi_list_with_grp_npi_locations(self, record, group_npi):
        logger.info(f"Inside get address for NPI {record.npi_number}")
        table_xpath = "//div[@id='ctl00_MainContent_pnlGvListPractice']/div/table/tbody/tr[position()>1]"
        addresses = []

        db = SessionLocal()
        try:
            db_plan = (record.health_plan or "").strip().lower()
            db_effective_date = record.effective_date

            # Get count of practice rows first
            practice_rows_count = len(self.driver.find_elements(By.XPATH, table_xpath))

            for i in range(1, practice_rows_count + 1):
                try:
                    # Get the row fresh each time to avoid stale elements
                    practice_row_xpath = f"{table_xpath}[{i}]"
                    practice_row = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, practice_row_xpath))
                    )
                    time.sleep(5)

                    # Extract address from the practice row
                    address_element = practice_row.find_element(
                        By.XPATH, ".//a[contains(@id,'LnkProvPractPlanAddress')]")
                    address = address_element.text.strip()
                    print(f"Extracted address for row {i}: {address}")

                    group_name = practice_row.find_element(
                        By.XPATH, ".//a[contains(@id,'LnkGroupName')]")
                    name = group_name.text.strip()

                    print(f"Extracted group name for row {i}: {group_name}")


                    address_data = pr_site_data.RequestAPi.split_address(address)
                    address_line_1 = address_data.get("address_line_1", "").upper()
                    address_line_2 = address_data.get("address_line_2", "").upper()
                    city = address_data.get("city", "").upper()
                    state = address_data.get("state", "").upper()
                    zipcode = address_data.get("zipcode", "")

                    # Check if this row is already expanded
                    try:
                        plan_tables = practice_row.find_elements(By.XPATH, ".//table[contains(@id,'GvProvPractPlans')]")
                        is_expanded = len(plan_tables) > 0
                    except:
                        is_expanded = False

                    # If not expanded, click the arrow to expand
                    if not is_expanded:
                        arrow_click = practice_row.find_element(By.XPATH, ".//a[contains(@id,'LnkExpandPract')]")
                        arrow_click.click()
                        time.sleep(2)

                        # Wait for expansion - use a more specific locator
                        WebDriverWait(self.driver, 15).until(
                            EC.presence_of_element_located(
                                (By.XPATH, f"{practice_row_xpath}//table[contains(@id,'GvProvPractPlans')]"))
                        )

                    # Get fresh reference to the row after expansion
                    practice_row = WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, practice_row_xpath))
                    )

                    # Find all plan tables within the practice row
                    plan_tables = practice_row.find_elements(By.XPATH, ".//table[contains(@id,'GvProvPractPlans')]")

                    for plan_table in plan_tables:
                        try:
                            # Get all plan rows (skip the header row)
                            plan_rows = plan_table.find_elements(
                                By.XPATH,
                                ".//tbody/tr[position()>1]"
                            )

                            for plan_row in plan_rows:
                                try:
                                    plan = plan_row.find_element(By.XPATH, "./td[2]").text.strip().lower()
                                    if plan != db_plan:
                                        continue

                                    effective_date = plan_row.find_element(By.XPATH, "./td[5]").text.strip()
                                    termination_date = plan_row.find_element(By.XPATH, "./td[6]").text.strip()

                                    # try:
                                    #     status_img = plan_row.find_element(By.XPATH,
                                    #                                        ".//td/img[contains(@src,'checkbox-checked-yes-small.png')]")
                                    #     has_green_tick = True
                                    # except:
                                    #     has_green_tick = False
                                    #
                                    # if not has_green_tick:
                                    #     print(f"Skipping NPI {record.npi_number}: No green tick in status")
                                    #     continue

                                    try:
                                        web_date = datetime.strptime(effective_date, "%m/%d/%Y").date()
                                    except ValueError:
                                        print(f"Invalid date format from web: {effective_date}")
                                        continue

                                    try:
                                        # Handle DB date format (assuming format like "Jan 01")
                                        db_date = datetime.strptime(db_effective_date, "%b %d").date().replace(
                                            year=web_date.year
                                        )
                                    except Exception as e:
                                        print(f"Invalid date format in DB for NPI {record.npi_number}: {e}")
                                        continue

                                    cleaned_zip_code = zipcode.replace("-", "") if zipcode else None
                                    npi_number = name.split('-')[
                                        -1].strip() if '-' in name else name.strip()
                                    npi_name = name.split('-')[
                                        0].strip() if '-' in name else name.strip()

                                    if web_date == db_date and not termination_date.strip():
                                        new_record = NPIAddress(
                                            npi=record.npi_number,
                                            address_line1=address_line_1,
                                            address_line2=address_line_2,
                                            city=city,
                                            state=state,
                                            zip_code=cleaned_zip_code,
                                            update=0,
                                            group_npi=npi_number,
                                            name=npi_name.upper()
                                        )
                                        db.add(new_record)
                                        db.commit()
                                        print(f"New record added for NPI {record.npi_number} with address '{address}'")

                                    addresses.append({
                                        "address_line_1": address_line_1,
                                        "address_line_2": address_line_2,
                                        "city": city,
                                        "state": state,
                                        "zipcode": zipcode,
                                        "update": 0,
                                        "group_npi": npi_number,
                                        "name": npi_name.upper()
                                    })
                                    logger.info(f"Out from get address for NPI {record.npi_number} with address '{address}'")

                                except Exception as e:
                                    print(f"Error processing plan row: {e}")
                                    continue

                        except Exception as e:
                            print(f"Error processing plan table: {e}")
                            continue

                except Exception as e:
                    print(f"Error processing practice row {i}: {e}")
                    continue

        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            db.close()

        return addresses

    def get_group_name_from_same_table(self, practice_row):
        """Extract group name from the same table/section as the address"""
        try:
            # Method 1: Find the header in the same parent div as the practice row
            group_header = practice_row.find_element(By.XPATH, "./ancestor::div[1]//h2[contains(text(), '-')]")
            full_group_text = group_header.text.strip()
            group_name = full_group_text.split('-')[0].strip()
            return group_name

        except Exception as e:
            print(f"Method 1 failed: {e}")
            try:
                # Method 2: Find the immediate parent container and look for h2
                parent_div = practice_row.find_element(By.XPATH, "./ancestor::div[position()=1]")
                group_header = parent_div.find_element(By.XPATH, ".//h2[contains(text(), '-')]")
                full_group_text = group_header.text.strip()
                group_name = full_group_text.split('-')[0].strip()
                return group_name

            except Exception as e:
                print(f"Method 2 failed: {e}")
                try:
                    # Method 3: Look for the closest h2 in the same section
                    group_header = practice_row.find_element(By.XPATH, "./preceding::h2[1]")
                    full_group_text = group_header.text.strip()
                    group_name = full_group_text.split('-')[0].strip()
                    return group_name

                except Exception as e:
                    print(f"Method 3 failed: {e}")
                    return "Unknown Group"











