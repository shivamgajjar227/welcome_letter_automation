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
            element = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(self.search_button)
            )
            element.click()
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

    def get_network(self):
        logger.info(f"Inside get Network")
        try:
            return self.driver.find_element(*self.network).text.strip()
            logger.info(f"Out from get Network")
        except NoSuchElementException:
            print("Network element not found.")
            return None

    def hover_over_practice_menu(self):
        logger.info(f"Inside Hover Over Practice Menu")
        provide_webelement = self.driver.find_element(*self.provider_menu)
        actions = ActionChains(self.driver)
        actions.move_to_element(provide_webelement).perform()
        time.sleep(5)
        sub_menu = self.driver.find_element(By.XPATH, "//a[@href='/ProvPractice.aspx']")
        sub_menu.click()
        logger.info(f"Out from Hover Over Practice Menu")

    def select_click_for_npi(self):
        self.click(self.click_for_npi)

    def get_group_npi(self):
        logger.info(f"Inside get Group NPI")
        try:
            element = WebDriverWait(self.driver, 10).until(
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

    def get_ind_npi_list_with_grp_npi_locations(self,record,group_npi,group_name):
        logger.info(f"Inside get Address ")
        table_xpath = "//div[@id='ctl00_MainContent_pnlGvListPractice']/div/table/tbody/tr"
        addresses = []

        db = SessionLocal()
        try:
            # Get NPI record from DB
            # npi_record = db.query(PRSiteData).filter(PRSiteData.npi_number ==).first()
            # if not npi_record:
            #     print(f"No active record found for NPI 1407236227")
            #     return []

            db_plan = (record.health_plan or "").strip().lower()
            db_effective_date = record.effective_date

            row_count = len(self.driver.find_elements(By.XPATH, table_xpath)) - 1

            for i in range(1, row_count + 1):
                try:
                    row = self.driver.find_element(By.XPATH, f"{table_xpath}{[i + 1]}")
                    time.sleep(3)

                    address_element = row.find_element(
                        By.XPATH, ".//a[contains(@id,'LnkProvPractPlanAddress')]")

                    address = address_element.text.strip()
                    print("Extracted address:", address)

                    address_data = pr_site_data.RequestAPi.split_address(address)

                    address_line_1 = address_data.get("address_line_1", "")
                    address_line_2 = address_data.get("address_line_2", "")
                    city = address_data.get("city", "")
                    state = address_data.get("state", "")
                    zipcode = address_data.get("zipcode", "")

                    arrow_click = row.find_element(By.XPATH, ".//td/div/div/div/a[contains(@id,'LnkExpandPract')]")
                    arrow_click.click()
                    time.sleep(3)

                    expanded_row = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, "//tbody/tr[2]"))
                    )
                    location_tables = expanded_row.find_elements(By.XPATH, "./td[1]/div[1]/div[1]")

                    for loc_table in location_tables:
                        try:
                            # address = loc_table.find_element(
                            #     By.XPATH,
                            #     "//td/div/div/div/a[contains(@id,'LnkProvPractPlanAddress')]"
                            # ).text.strip().upper()

                            # address_data = pr_site_data.RequestAPi.split_address(address)
                            #
                            # address_line_1 = address_data.get("address_line_1","" )
                            # address_line_2 = address_data.get("address_line_2", "")
                            # city = address_data.get("city", "")
                            # state = address_data.get("state", "")
                            # zipcode = address_data.get("zipcode", "")
                            # remarks = address_data.get("remarks", "")

                            rows = loc_table.find_elements(
                                By.XPATH,
                                "//table[@id='ctl00_MainContent_GvProvPractice_ctl02_GvProvPractPlans']/tbody/tr[position()>1]"
                            )

                            for inner_row in rows:
                                try:
                                    plan = inner_row.find_element(By.XPATH, "./td[2]").text.strip().lower()
                                    if plan != db_plan:
                                        continue

                                    effective_date = inner_row.find_element(By.XPATH, "./td[5]").text.strip()
                                    termination_date = inner_row.find_element(By.XPATH, "./td[6]").text.strip()

                                    try:
                                        web_date = datetime.strptime(effective_date, "%m/%d/%Y").date()
                                    except ValueError:
                                        print(f"Invalid date format from web: {effective_date}")
                                        continue

                                    try:
                                        db_date = datetime.strptime(db_effective_date, "%b %d").date().replace(
                                            year=web_date.year
                                        )
                                    except Exception as e:
                                        print(f"Invalid date format in DB for NPI {record.npi_number}: {e}")
                                        continue
                                    cleaned_zip_code = zipcode.replace("-", "") if zipcode else None
                                    npi_number = group_npi.split('-')[-1].strip()
                                    npi_name = group_name.split('-')[0].strip()

                                    if web_date == db_date and termination_date == "":

                                        new_record = NPIAddress(
                                            npi=record.npi_number,
                                            address_line1=address_line_1,
                                            address_line2=address_line_2,
                                            city=city,
                                            state=state,
                                            zip_code=cleaned_zip_code,
                                            update=0,
                                            group_npi = npi_number,
                                            name = npi_name
                                        )
                                        db.add(new_record)
                                        db.commit()
                                        print(
                                            f"New record added for NPI {record.npi_number} with address '{address}'")

                                    addresses.append({
                                    "address_line_1": address_line_1,
                                    "address_line_2": address_line_2,
                                    "city": city,
                                    "state": state,
                                    "zipcode": zipcode,
                                    "update": 0,
                                    "group_npi": npi_number,
                                    "name": npi_name,
                                })
                                    continue
                                    logger.info(f"Out from get Address")

                                except Exception as e:
                                    print(f"Error processing plan row: {e}")
                                    continue

                        except Exception as e:
                            print(f"Error processing location table: {e}")
                            continue

                except Exception as e:
                    print(f"Error processing outer row {i}: {e}")
                    continue

        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            db.close()

        return addresses











