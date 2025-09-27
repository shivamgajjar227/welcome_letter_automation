import time
from models import NPIAddress
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from constants import TEMPLATE_MAP
import api.pr_site_data
from sqlalchemy.orm import Session
from db.session import SessionLocal
import constants
from selenium.common.exceptions import NoAlertPresentException
from pages.base_page import BasePage
from selenium.common.exceptions import TimeoutException, NoSuchElementException,ElementClickInterceptedException
from core import loggin_utils
import logging

log_name =  "QuickcapPage"
logger_setup = loggin_utils.setup_logger(log_name, level='INFO')
logger = logging.getLogger(log_name)

class QuickcapPage(BasePage):

    USERNAME_FIELD = (By.XPATH, "//input[@id='TaRtxt_username']")
    PASSWORD_FIELD = (By.XPATH, "//input[@id='TaRpas_password']")
    LOGIN_BUTTON = (By.XPATH, "//input[@value='LOGIN']")
    select_company = (By.XPATH, "//td[@class='clientBold']//a[@id='comptda_DNSWC']")
    credentialing_tab = (By.XPATH, "(//h3[normalize-space()='Credentialing'])[1]")
    practitioner_data = (By.XPATH, "//a[normalize-space()='Practitioner Data']")
    npi_fields = (By.XPATH, "//input[@id='Sr_Tatxt_npi']")
    quick_add_button = (By.CSS_SELECTOR, "input[value='Quick Add']")
    categories_drowpdown = (By.XPATH, "//select[@id='Rslt_prac_category']")
    quick_add_window_npi_button = (By.XPATH, "//input[@id='TaRtxt_npi_number']")
    select_provider_type = (By.XPATH, "(//select[@id='Rslt_provider_type']/option)[3]")
    provide_id_field = (By.XPATH, "//input[@id='TaRtxt_provider_id']")
    primary_specialist =  (By.XPATH,"//a[@class='chosen-single chosen-default trackAtt']")
    last_name = (By.XPATH, "//textarea[@id='TaRara_last_name']")
    first_name = (By.XPATH, "//input[@id='Tatxt_first_name']")
    suffix = (By.XPATH, "//select[@id='Taslt_prof_suffix']")
    gender = (By.XPATH, "//select[@id='Taslt_sex']")
    birthdate = (By.XPATH, "//input[@id='Dttxt_date_of_birth']")
    contract_type = (By.XPATH, "//select[@id='Rslt_contract_type']")
    contract_from_date = (By.XPATH, "//input[@id='DtRtxt_ContractFromDate']")
    payment_type = (By.XPATH, "//select[@id='Rslt_PaymentType']")
    account = (By.XPATH, "//select[@id='Rslt_AccountNo']")
    organization = (By.CSS_SELECTOR, "#img_for_org_0")
    npi_org = (By.CSS_SELECTOR, "#Sr_Tatxt_OrgNPI")
    search_npi = (By.XPATH, "//input[@name='btn_search_submit']")
    organizational_type = (By.XPATH, "//select[@id='org_type_0']")
    org_effective_from = (By.XPATH, "//input[@id='ve_date_effective_from_0']")
    availability = (By.CSS_SELECTOR, "#availability_0")
    practice_type = (By.XPATH, "//select[@id='Rslt_practice_type']")
    name = (By.XPATH, "//input[@id='TaRtxt_LocationName']")
    address1=(By.XPATH, "//input[@id='TaRtxt_Address1']")
    address_line_2 = (By.XPATH, "//input[@id='Tatxt_street_2']")
    city = (By.XPATH, "//input[@id='TaRtxt_city']")
    state = (By.XPATH, "//select[@id='Rslt_state']")
    zip = (By.XPATH, "//input[@id='TaRtxt_zip']")
    save = (By.XPATH, "//input[@value='Save']")
    agree = (By.XPATH, "//iframe[@id='TB_iframeContent']")
    close = (By.XPATH, "//a[normalize-space()='Close']")
    cancel = (By.XPATH, "//input[@value='Cancel']")
    speciality = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Medical_Info_lblDegree")
    change_company = (By.XPATH, "//a[normalize-space()='Change Company']")
    select_company_next = (By.XPATH, "//body[1]/table[1]/tbody[1]/tr[2]/td[1]/table[1]/tbody[1]/tr[1]/td[1]/form[1]/table[1]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[1]/td[1]/table[1]")
    org_id = (By.CSS_SELECTOR, "td[valign='top'] a[class='trackAtt']")
    templet = (By.XPATH, "//select[@id='slt_CONTRACT_TEMPLATE_ID']")
    username_in_company_prompt = (By.XPATH, "//input[@id='username']")
    password_in_company_prompt = (By.XPATH, "(//input[@id='userpass'])[1]")
    login_button_in_company_prompt = (By.XPATH, "//input[@id='btnSumit']")
    org_name = (By.XPATH, "//input[@id='org_name_0']")
    links_handler = (By.XPATH, "//img[@id='links_handler']")
    click_search = (By.XPATH, "//input[@id='btn_Search']")
    click_edit = (By.XPATH, "//img[@title='Edit']")
    click_provider = (By.XPATH, "//a[normalize-space()='Providers']")
    add_provider = (By.CSS_SELECTOR, "input[value='Add Provider']")
    last_name1 = (By.XPATH, "//textarea[@id='TaRara_LastName']")
    first_name1 = (By.XPATH, "//input[@id='Tatxt_FirstName']")
    effective_date = (By.XPATH, "//input[@id='DtRtxt_ActiveFromDate']")
    primary_speciality = (By.XPATH, "//a[@class='chosen-single chosen-default trackAtt']")
    provider_type1 = (By.XPATH, "//option[normalize-space()='HDO']")
    add_new_location = (By.XPATH, "//input[@id='chk_add_new_location']")
    name1 = (By.XPATH, "//input[@id='Tatxt_LocationName']")
    address2 = (By.CSS_SELECTOR, "#Tatxt_Address1")
    address_line2 = (By.CSS_SELECTOR, "#Tatxt_Address2")
    zip1 = (By.CSS_SELECTOR, "#Tatxt_zip")
    city1 = (By.XPATH, "//input[@id='Tatxt_city']")
    save1 = (By.XPATH, "//input[@id='btn_submit']")
    cancel1 = (By.XPATH, "//input[@value='Cancel']")
    credentialing_tab1 = (By.XPATH, "(//h3[normalize-space()='Credentialing'])[1]")
    primary = (By.XPATH, "//input[@id='check_location_NEW_OFFICE_1']")
    provider_letter = (By.XPATH, "//input[@id='provider_id_suffix']")
    no_data_find = (By.XPATH, "//td[normalize-space()='No data found']")
    primary_specialist1 =  (By.XPATH,"//div[@id='Rslt_PrimarySpecialty_chosen']/a")
    edit_for_healthplan = (By.XPATH, "//img[@title='Edit']")
    health_panel_plan = (By.XPATH, "//input[@value='Health Plan Panel']")
    membership_start_date = (By.XPATH, "//input[@id='DtRtxt_ActiveFromDate']")
    click_plus = (By.XPATH, "//a[@onclick='$.addDosRow();']//img")
    save_healthplan = (By.XPATH, "//input[@value='Save']")
    other_ids = (By.XPATH, "//div[11]//a[1]")
    add_plus = (By.XPATH, "//img[@src='images/plus_add.gif']")
    taxonomy_dropdown = (By.XPATH, "//tbody/tr/td/select[contains(@name,'new_other_id')]")
    provider_id_dropdown = (By.XPATH, "//tbody/tr/td/select[contains(@name,'new_provider_id')]")
    taxonomy_no = (By.XPATH, "(//tbody/tr/td/input[@type='text'][@class='comn-input'][@size='15'])[last()]")
    save_taxonomy = (By.XPATH, "//input[@id='btn_submit']")




    def login(self, username, password):
        logger.info(f"Inside quickcap login funct")
        self.enter_text(self.USERNAME_FIELD, username)
        self.enter_text(self.PASSWORD_FIELD, password)
        self.click(self.LOGIN_BUTTON)
        logger.info("Out from Quickcap logging func")

    def choose_company(self, company_name):
        print(f"🔍 Attempting to click login icon for: {company_name}")
        logger.info(f"Inside choose company: {company_name}")
        try:
            company_icon = WebDriverWait(self.driver, 20).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    f"//td[normalize-space(text())='{company_name}']/preceding-sibling::td[1]//img[@title='Log-in']"
                )),
                message=f"Login icon for '{company_name}' not clickable within 20 seconds."
            )

            # STEP 3 — Scroll and click
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", company_icon)
            self.driver.execute_script("arguments[0].click();", company_icon)

            print(f"✅ Successfully switched to: {company_name}")
            logger.info("Out from choose company")
            return True

        except Exception as e:
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message:{str(e)}")
            logger.exception(f"Error in qc choose company: {e}")
            self.driver.save_screenshot(f"error_login_icon_{company_name.replace(' ', '_')}.png")
            return False

    def choose_credentialing_tab(self):
        logger.info(f"Inside Choose Credentialing Tab")
        # self.wait_for_element_present(self.credentialing_tab)
        try:
            element = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.credentialing_tab)
            )
            element.click()
            logger.info(f"Out from Credentialing Tab")
        except Exception as e:
            print(f"<UNK> Failed to click credentialing tab: {e}")

    def choose_practitioner_data(self):
        logger.info(f"Inside Choose Practitioner Data")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.practitioner_data)
            ).click()
            print("Practitioner data selected successfully.")
            logger.info(f"Out from Practitioner Data")
        except Exception:
            print("Error: No practitioner data found or clickable.")

    def enter_npi(self, npi):
        logger.info(f"Inside Enter NPI")
        try:
            logger.info(f"Inside enter npi: {npi}")
            self.click(self.npi_fields)
            self.enter_text(self.npi_fields, npi)
            print(f"NPI entered successfully: {npi}")
            logger.info(f"Out from Enter NPI")
        except Exception as e:
            print(f"Error in enter_npi while entering NPI '{npi}': {e}")

    def accept_alert(self, timeout=5):
        logger.info(f"Inside Accept Alert")
        """
        Waits for an alert up to `timeout` seconds and clicks OK if present.
        """
        try:
            for _ in range(timeout):
                try:
                    alert = self.driver.switch_to.alert
                    print("Alert text:", alert.text)  # optional
                    alert.accept()  # ✅ Click OK
                    print("Alert accepted.")
                    return True
                except NoAlertPresentException:
                    time.sleep(1)
            print("No alert appeared.")
            return False
            logger.info(f"Out from Accept Alert")

        except Exception as e:
            print(f"Error while handling alert: {e}")
            return False

    def click_credential_button(self):
        try:
            quick_add_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//tbody/tr/td/input[@value='Credential ']"))
            )
            quick_add_btn.click()
            print("✅ Quick Add button clicked successfully.")
        except Exception as e:
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message:{str(e)}")

    def check_no_data_found_text(self):
        try:
            get_no_data_found_text = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//td[normalize-space()='No data found']"))
            ).text.strip()
            return get_no_data_found_text
        except Exception as e:
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: Element 'No data found' not visible within timeout")

    def dismiss_alert(self, timeout=5):
        logger.info(f"Inside Dismiss Alert")
        """
        Waits for alert up to `timeout` seconds and clicks Cancel if present.
        """
        try:
            for _ in range(timeout):
                try:
                    alert = self.driver.switch_to.alert
                    print("Alert text:", alert.text)  # optional
                    alert.dismiss()  # Click Cancel
                    print("Alert dismissed (Cancel clicked).")
                    return True
                except NoAlertPresentException:
                    time.sleep(1)
            print("No alert appeared.")
            return False
            logger.info(f"Out from Dismiss Alert")

        except Exception as e:
            print(f"An error occurred while dismissing alert: {e.msg}")
            return False

    def click_quick_add_button(self):
        logger.info(f"Inside Click Quick Add Button")
        try:
            # Try multiple selectors with JavaScript click to avoid staleness
            selectors = [
                "//input[@value='Quick Add']",
                "//button[contains(text(), 'Quick Add')]",
                "//a[contains(text(), 'Quick Add')]",
                "//*[contains(@onclick, 'QuickAdd') or contains(@id, 'QuickAdd')]"
            ]

            for selector in selectors:
                try:
                    element = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, selector))
                    )
                    self.driver.execute_script("arguments[0].click();", element)
                    print("✅ Quick Add button clicked successfully via JavaScript.")
                    return True
                except:
                    continue

            print("❌ Quick Add button not found with any selector.")
            return False
            logger.info(f"Out from Click Quick Add Button")

        except Exception as e:
            print(f"⚠️ Unexpected error while clicking Quick Add button: {e}")
            return False

    def select_category_dropdown(self, value):
        logger.info(f"Inside Select Category Dropdown:{value}")
        try:
            # Wait until dropdown is present
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//select[@id='Rslt_prac_category']"))
            )
            dropdown = Select(element)
            dropdown.select_by_visible_text(value)
            print(f"Category '{value}' selected successfully.")
            logger.info(f"Out from Select Category Dropdown:{value}")
        except Exception as e:
            print(f"Error selecting category '{value}': {e}")
        # self.click(self.categories_drowpdown)

    def click_quick_add_window_npi_button(self, npi):
        logger.info(f"Inside Click Quick Add Window NPI Button:{npi}")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.quick_add_window_npi_button)
            ).click()

            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.quick_add_window_npi_button)
            ).send_keys(npi)
            print(f"NPI '{npi}' entered successfully.")
            logger.info(f"Out from Click Quick Add Window NPI Button:{npi}")

        except Exception as e:
            print(f"Error in click_quick_add_window_npi_button: {e}")

    def select_provider_type_dropdown(self, category: str, network: str, speciality: str):
        logger.info(
            f"Inside Select Provider Type Dropdown with category: {category}, network: {network}, speciality: {speciality}")
        try:
            # Step 1: Locate the dropdown element
            dropdown_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//select[@id='Rslt_provider_type']"))
            )
            dropdown = Select(dropdown_element)

            # Step 2: Get all available options as text
            options = [opt.text.strip() for opt in dropdown.options]
            value_to_select = None

            # Step 3: Normalize inputs
            category = category.strip().upper() if category else ""
            network = network.strip().upper() if network else ""
            speciality = speciality.strip().upper() if speciality else ""

            # Step 4: Determine value to select based on logic
            if category in ["MD", "DO", "DPM"]:
                if network == "PODIATRY" and "PODIATRIST" in options:
                    value_to_select = "PODIATRIST"
                elif network == "ORTHOPEDICS" and "ORTHOPEDICS" in options:
                    value_to_select = "ORTHOPEDICS"
                elif network == "DERMATOLOGY":
                    if "MOHS" in speciality and "MOHS SURGEON AND GENERAL" in options:
                        value_to_select = "MOHS SURGEON AND GENERAL"
                    elif "GENERAL DERMATOLOGY" in options:
                        value_to_select = "GENERAL DERMATOLOGY"
                else:
                    if "SPECIALIST" in options:
                        value_to_select = "SPECIALIST"
            else:
                if "PHYSICIAN EXTENDER" in options:
                    value_to_select = "PHYSICIAN EXTENDER"

            # Step 5: Select the value if found
            if value_to_select:
                dropdown.select_by_visible_text(value_to_select)
                print(f"Provider type '{value_to_select}' selected successfully.")
                logger.info(f"Out from Select Provider Type Dropdown: {value_to_select}")
            else:
                print("No matching provider type found in dropdown.")
                logger.warning("Provider type not found in dropdown.")

        except Exception as e:
            print(f"Error selecting provider type: {e}")
            logger.error(f"Error selecting provider type: {e}")

    def enter_provider_id(self, value):
        logger.info(f"Inside Enter Provider ID:{value}")
        try:
            field = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.provide_id_field)
            )
            field.clear()
            field.send_keys(value)
            print(f"Provider ID '{value}' entered successfully.")
            logger.info(f"Out from Enter Provider ID:{value}")

        except Exception as e:
            print(f"Error in entering provider ID: {e}")

    def select_primary_speciality_dropdown(self, network_value):
        logger.info(f"Inside Select Primary Speciality Dropdown:{network_value}")
        try:
            mapped_value = constants.PRIMARY_SPECIALITY_MAP.get(network_value)
            if not mapped_value:
                print(f"⚠️ No mapping found for: {network_value}")
                return

            wait = WebDriverWait(self.driver, 10)

            # Open dropdown
            wait.until(EC.element_to_be_clickable(self.primary_specialist)).click()

            # Build xpath for option
            option_xpath = f"//div[@id='Rslt_specialty_chosen']//li[normalize-space(text())='{mapped_value}']"

            # Wait until option is visible
            option = wait.until(EC.visibility_of_element_located((By.XPATH, option_xpath)))

            # Extra check: scroll into view before clicking
            self.driver.execute_script("arguments[0].scrollIntoView(true);", option)

            # Now click
            option.click()

            print(f"✅ Selected: {mapped_value}")
            logger.info(f"Out from Select Primary Speciality Dropdown:{network_value}")

        except Exception as e:
            print(f"❌ Dropdown selection failed: {str(e)}")

    def enter_last_first_name(self, last_name, first_name):
        logger.info(f"Inside Enter Last First Name:{last_name,first_name}")
        try:
            self.enter_text(self.last_name, last_name)
            self.enter_text(self.first_name, first_name)
            print(f"Entered Last Name: '{last_name}', First Name: '{first_name}' successfully.")
            logger.info(f"Out from Enter Last First Name:{last_name, first_name}")

        except Exception as e:
            print(f"Error in entering last and first name: {e}")

    def select_gender(self, value):
        logger.info(f"Inside Select Gender:{value}")
        try:
            dropdown_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//select[@id='Taslt_sex']"))
            )
            Select(dropdown_element).select_by_visible_text(value)
            print(f"Gender '{value}' selected successfully.")
            logger.info(f"Out from Select Gender:{value}")

        except Exception as e:
            print(f"Error in selecting gender '{value}': {e}")

    def enter_birthdate(self, value):
        self.enter_text(self.birthdate, value)

    def select_contract_type(self, value):
        logger.info(f"Inside Select Contract Type:{value}")
        try:
            dropdown_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//select[@id='Rslt_contract_type']"))
            )
            Select(dropdown_element).select_by_visible_text(value)
            print(f"Contract type '{value}' selected successfully.")
            logger.info(f"Out from Select Contract Type:{value}")

        except Exception as e:
            print(f"Error in selecting contract type '{value}': {e}")

    def enter_contract_from_date(self, value):
        logger.info(f"Inside Enter Contract From Date:{value}")
        try:
            self.enter_text(self.contract_from_date, value)
            print(f"Contract From Date entered successfully: {value}")
            logger.info(f"Out from Enter Contract From Date:{value}")
        except Exception as e:
            print(f"Error in enter_contract_from_date while entering '{value}': {e}")

    def select_payment_type(self, value):
        logger.info(f"Inside Select Payment Type:{value}")
        try:
            dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_PaymentType']"))
            dropdown.select_by_visible_text(value)
            print(f"Payment type selected successfully: {value}")
            logger.info(f"Out from Select Payment Type:{value}")
        except Exception as e:
            print(f"Error in select_payment_type while selecting '{value}': {e}")

    def select_account(self, value):
        logger.info(f"Inside Select Account:{value}")
        try:
            dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_AccountNo']"))
            dropdown.select_by_visible_text(value)
            print(f"Account '{value}' selected successfully.")
            logger.info(f"Out from Select Account:{value}")

        except Exception as e:
            print(f"Error in selecting account '{value}': {e}")

    # def switch_to_new_window(self):
    #     time.sleep(1)
    #     handles = self.driver.window_handles
    #     self.driver.switch_to.window(handles[-1])  # switch to latest opened window

    def switch_to_previous_window(self):
        handles = self.driver.window_handles
        self.driver.switch_to.window(handles[1])

    def switch_to_main_window(self):
        self.driver.switch_to.window(self.driver.window_handles[0])
        self.driver.get("https://your.main.quickcap.page.url")

    def select_org_from_popup(self, org_name="ABC ORG NAME"):
        try:
            org_row = f"//td[normalize-space()='{org_name}']"
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, org_row))
            ).click()
            print(f"✔ Selected organization: {org_name}")
        except Exception:
            print(f"⚠ Organization '{org_name}' not found. Skipping selection.")

    def click_organization(self):
        logger.info(f"Inside Click Organization")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.organization)
            ).click()
            print("Organization button clicked successfully.")
            logger.info(f"Out from Click Organization")
        except Exception as e:
            print(f"Error in click_organization: {e}")

    def enter_npi_org(self, value):
        logger.info(f"Inside Enter NPI Org:{value}")
        try:
            self.enter_text(self.npi_org, value)
            print(f"NPI Org entered successfully: {value}")
            logger.info(f"Out from Enter NPI Org:{value}")
        except Exception as e:
            print(f"Error in enter_npi_org while entering '{value}': {e}")

    def click_search_npi(self):
        logger.info(f"Inside Click Search NPI")
        try:
            element = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(self.search_npi)
            )
            element.click()
            print("Search NPI button clicked successfully.")
            logger.info(f"Out from Click Search NPI")
        except Exception as e:
            print(f"Error in click_search_npi: {e}")

    def select_organizational_type(self, value):
        dropdown_element = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//select[@id='org_type_0']"))
        )
        Select(dropdown_element).select_by_visible_text(value)

    def enter_org_effective_from(self, value):
        self.enter_text(self.org_effective_from, value)

    def select_availability(self, value):
        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='availability_0']"))
        dropdown.select_by_visible_text(value)

    def select_practice_type(self, value):
        logger.info(f"Inside Select Practice Type:{value}")
        try:
            dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_practice_type']"))
            dropdown.select_by_visible_text(value)
            logger.info(f"Out from Select Practice Type:{value}")

        except Exception as e:
            print(f"Error in select practice type: {e}")


    def enter_name(self, value):
        logger.info(f"Inside Enter Name:{value}")
        try:
            self.enter_text(self.name, value)
            logger.info(f"Out from Enter Name:{value}")

        except Exception as e:
            print(f"Error in entering name: {e}")


    def enter_address1(self, value):
        logger.info(f"Inside Enter Address1:{value}")
        try:
            self.enter_text(self.address1, value)
            print(f"Address1 '{value}' entered successfully.")
            logger.info(f"Out from Enter Address1:{value}")

        except Exception as e:
            print(f"Error in entering Address1: {e}")

    def enter_address_line_2(self, value):
        logger.info(f"Inside Enter Address Line2:{value}")
        try:
            self.enter_text(self.address_line_2, value)
            print(f"Address1 '{value}' entered successfully.")
            logger.info(f"Out from Enter Address Line2:{value}")

        except Exception as e:
            print(f"Error in entering Address1: {e}")

    def enter_city(self, value):
        logger.info(f"Inside Enter City:{value}")
        try:
            self.enter_text(self.city, value)
            print(f"City '{value}' entered successfully.")
            logger.info(f"Out from Enter City:{value}")

        except Exception as e:
            print(f"Error in entering city: {e}")

    def select_state(self, value):
        logger.info(f"Inside Select State1:{value}")
        try:
            dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Taslt_state']"))
            dropdown.select_by_visible_text(value)
            print(f"State selected successfully: {value}")
            logger.info(f"Out from Select State1:{value}")
        except Exception as e:
            print(f"Error in select_state1 while selecting '{value}': {e}")

    def enter_zip(self, value):
        logger.info(f"Inside Enter ZIP:{value}")
        try:
            self.enter_text(self.zip, value)
            print(f"ZIP '{value}' entered successfully.")
            logger.info(f"Out from Enter ZIP:{value}")

        except Exception as e:
            print(f"Error in entering ZIP: {e}")

    def click_save(self):
        logger.info(f"Inside Click Save")
        try:
            self.click(self.save)
            print("Save button clicked successfully.")
            logger.info(f"Out from Click Save")

        except Exception as e:
            print(f"Error in clicking Save button: {e}")

    def select_speciality(self, network):
        logger.info(f"Inside Select Speciality:{network}")
        try:
            wait = WebDriverWait(self.driver, 10)
            self.click(self.primary_specialist)

            # Step 2: Define option mapping (adjust text as it appears in UI)
            option_map = {
                "podiatry": "//li[contains(normalize-space(), 'POD - PODIATRY')]",
                "dermatology": "//li[contains(normalize-space(), 'D - DERMATOLOGY')]",
                "orthopedic": "//li[contains(normalize-space(), 'ORT - ORTHOPEDICS')]",
                "pain management": "//li[contains(normalize-space(), 'APM - Anesthesiology/Pain Management')]",
                "cardiology": "//li[contains(normalize-space(), 'CAR - CARDIOLOGY')]",
                "neurology": "//li[contains(normalize-space(), 'NEU - NEUROLOGY')]",
                "podiatry, wound care": "//li[contains(normalize-space(), 'POD - PODIATRY')]"
            }

            # Step 3: Get correct xpath
            option_xpath = option_map.get(network)
            if not option_xpath:
                raise ValueError(f"No speciality mapping found for: {network}")

            option = wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
            option.click()
            print(f"✅ Selected speciality for {network}")
            logger.info(f"Out from Select Speciality:{network}")

        except Exception as e:
            print(f"❌ Failed to click speciality: {str(e)}")

    def click_agree_inside_iframe(self):
        # Wait until iframes are present
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "iframe"))
        )

        # Get all iframes
        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Found {len(iframes)} iframes on the page.")

        # Loop through each iframe to find the one with the "Agree" button
        for idx, frame in enumerate(iframes):
            try:
                self.driver.switch_to.frame(frame)
                print(f"Switched to iframe #{idx}")

                # Wait and check if the agree button is present and clickable
                agree_button = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, "//input[@value='I agree']"))
                )
                agree_button.click()
                print(f"✅ Clicked 'Agree' button in iframe #{idx}")
                break  # Exit after clicking
            except Exception as e:
                self.driver.switch_to.default_content()
                print(f" 'Agree' not found in iframe #{idx}: {e}")
                continue

    def click_cancel(self):
        # Wait until iframes are present
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, "iframe"))
        )

        iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Found {len(iframes)} iframes on the page.")

        for idx, frame in enumerate(iframes):
            try:
                self.driver.switch_to.frame(frame)
                print(f"Switched to iframe #{idx}")

                # Try finding and clicking the close/cancel button
                WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable(self.close)
                ).click()
                print(f"✅ Clicked cancel/close in iframe #{idx}")
                break
            except Exception as e:
                print(f" Cancel not found in iframe #{idx}: {e}")
                self.driver.switch_to.default_content()
                continue

        self.driver.switch_to.default_content()

    def cancel_button_click_quick_add(self):
        """Clicks the cancel button in the quick add window"""
        try:
            # First try to find and click the cancel button
            cancel_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//input[@value='Cancel']"))
            )
            cancel_btn.click()
            print("Clicked cancel button in quick add window")
            return True
        except Exception as e:
            print(f"Failed to click cancel button: {str(e)}")
            return False

    def click_change_companyy(self):
        """Clicks the 'Change Company' link"""
        try:
            # Using the locator you provided
            change_company_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[normalize-space()='Change Company']"))
            )
            change_company_link.click()
            print("Clicked 'Change Company' link")
            return True
        except Exception as e:
            print(f"Failed to click Change Company link: {str(e)}")
            return False

    def get_company_code(network: str, health_plan: str) -> str:
        prefix_map = {
            "dermatology": "DNS",
            "pain management": "PM",
            "podiatry": "PNS",
            "orthopedic": "ONS"
        }

        prefix = prefix_map.get(network.strip().lower())
        if not prefix:
            raise ValueError(f"Invalid network: {network}")

        # Clean health plan (remove spaces, handle casing)
        formatted_plan = health_plan.strip().replace(" ", "").title()

        return f"{prefix} {formatted_plan}"

    def handle_confirmation_popup(self, button_text):
        """Handles confirmation popups by clicking specified button"""
        try:
            popup = WebDriverWait(self.driver, 5).until(
                EC.alert_is_present()
            )
            if button_text in popup.text:
                popup.accept()
            else:
                popup.dismiss()
            return True
        except:
            # If no alert found, try finding a modal dialog button
            try:
                button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, f"//button[contains(., '{button_text}')]")
                    )
                )
                button.click()
                return True
            except Exception as e:
                print(f"Failed to handle confirmation popup: {str(e)}")
                return False

    def click_org_id(self, npi_number: str, address_line1: str) -> bool:
        """
        Clicks the Org ID for the given NPI.
        Returns True if successful, False if Org ID not found.
        Updates remarks in NPIAddress table if Org ID not found.
        """
        logger.info(f"Inside Click Org ID: {npi_number}")
        db: Session = SessionLocal()
        main_window = self.driver.window_handles[0]

        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.org_id)
            )
            self.driver.execute_script("arguments[0].click();", element)
            print("✅ Organization ID clicked successfully")
            logger.info(f"Out from Click Org ID: {npi_number}")
            return True

        except Exception as e:
            error_message = "Organization ID not found or clickable"
            print(f"❌ {error_message}")

            # Update only remarks
            try:
                db.query(NPIAddress).filter(
                    NPIAddress.address_line1 == address_line1,
                    NPIAddress.npi == npi_number,
                    NPIAddress.update == 0
                ).update({"remarks": error_message[:500]})
                db.commit()
                logger.info(f"Remarks updated for NPI {npi_number}")
            except Exception as db_error:
                print(f"Database update error: {db_error}")
            finally:
                db.close()

            # Close current (Org) tab if open
            try:
                all_windows = self.driver.window_handles
                current_window = self.driver.current_window_handle

                if current_window != main_window:
                    # Close Org popup first
                    self.driver.close()
                    print("🔒 Org ID popup closed.")

                    # Switch to next window (if exists) and close it too
                    all_windows = self.driver.window_handles
                    if len(all_windows) > 1:
                        self.driver.switch_to.window(all_windows[-1])
                        self.driver.close()
                        print("🔒 Next window closed.")

                    # Finally switch back to main window
                    self.driver.switch_to.window(main_window)
                    print("✅ Returned to main window.")
                    logger.info(f"Out from Click Org ID: {npi_number}")

            except Exception as win_err:
                print(f"Window handling error: {win_err}")

            return False

    def ensure_credentialing_tab(self):
        logger.info(f"Inside Ensure Credentialing Tab")
        try:
            # Check if Credentialing tab is visible
            tabs = self.driver.find_elements(By.XPATH, "//a[contains(text(),'Credentialing')]")
            if tabs:
                print("✅ Credentialing tab is already visible.")
                return True

            # If not visible, click the arrow to expand menu
            print("⚠️ Credentialing tab not found. Expanding menu...")
            arrow_button = self.driver.find_element(By.XPATH, "//div[@id='menu']//span[@class='arrow']")
            arrow_button.click()
            time.sleep(2)

            # Check again after expanding
            tabs = self.driver.find_elements(By.XPATH, "//a[contains(text(),'Credentialing')]")
            if tabs:
                print("✅ Credentialing tab is now visible after expanding.")
                return True
            else:
                print("❌ Credentialing tab still not found even after expanding.")
                return False
            logger.info(f"Out from Ensure Credentialing Tab")
        except Exception as e:
            print(f"Error ensuring Credentialing tab: {e}")
            return False

    def select_contract_template(self, company_name: str):
        logger.info(f"Inside Select Contract Template:{company_name}")
        try:
            dropdown_value = TEMPLATE_MAP.get(company_name)

            if not dropdown_value:
                raise ValueError(f"No contract template mapping found for company: {company_name}")

            dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='slt_CONTRACT_TEMPLATE_ID']"))
            dropdown.select_by_visible_text(dropdown_value)
            print(f"Contract template for company '{company_name}' selected as '{dropdown_value}'.")
            logger.info(f"Out from Select Contract Template:{company_name}")

        except Exception as e:
            print(f"Error in selecting contract template for company '{company_name}': {e}")

    def click_change_company(self):
        logger.info(f"Inside Click Change Company")
        try:
            change_company_button = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.change_company)
            )
            change_company_button.click()
            logger.info(f"Out from Click Change Company")

        except Exception as e:
            print(f"Error: {e}")
            print("Current URL:", self.driver.current_url)
            print("Title:", self.driver.title)
            self.driver.save_screenshot("change_company_error.png")
            raise

    def enter_username_in_company_prompt(self, value):
        logger.info(f"Inside Enter Username in Company Prompt:{value}")
        try:
            self.enter_text(self.username_in_company_prompt, value)
            print(f"Username '{value}' entered successfully in company prompt.")
            logger.info(f"Out from Enter Username in Company Prompt:{value}")

        except Exception as e:
            print(f"Error in entering username in company prompt: {e}")

    def enter_password_in_company_prompt(self, value):
        logger.info(f"Inside Enter Password in Company Propmt:{value}")
        try:
            self.enter_text(self.password_in_company_prompt, value)
            print("Password entered successfully in company prompt.")
            logger.info(f"Out from Enter Password in Company Propmt:{value}")

        except Exception as e:
            print(f"Error in entering password in company prompt: {e}")

    def click_login_button_in_company_prompt(self):
        logger.info(f"Inside Click Login Button in Company Prompt")
        try:
            element = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(self.login_button_in_company_prompt)
            )
            element.click()
            print("Login button in company prompt clicked successfully.")
            logger.info(f"Out from Click Login Button in Company Prompt")

        except Exception as e:
            print(f"Error in clicking login button in company prompt: {e}")

    def get_org_name(self):

        org_name_wait = WebDriverWait(self.driver,10).until(
            EC.visibility_of_element_located(self.org_name)
        )
        org_name = org_name_wait.text.strip()
        return org_name

    def get_company_xpath(self, company_code):
        image_path = f"./../general/images/fancy/{company_code}.gif"
        self.driver.find_element(By.XPATH,f'//a[@onclick="showLogin(\'{company_code}\', \'{company_code}\', \'{image_path}\');"]//img[@title="Log-in"]').click()

    def driver_close(self):
        self.driver.quit()

    def click_links_handler(self):
        """Clicks the links handler button if present, otherwise continues silently"""
        try:
            # Short timeout since this is an optional element
            WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable(self.links_handler)
            ).click()
            print("Links handler button clicked")
            return True
        except TimeoutException:
            return True  # Consider this a success since we want to proceed either way
        except Exception as e:
            print(f"Unexpected error clicking links handler: {str(e)}")
            return True

    def click_company(self):
        logger.info(f"Inside of Click Company ")
        try:
            self.click(self.select_company)
            logger.info(f"Out from Click Company")
        except Exception as e:
            print(f"Error in click company: {e}")


    def click_search_button(self):
        logger.info(f"Inside Click Search Button")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.click_search)
            ).click()
            print("Search button clicked successfully.")
            logger.info(f"Out from Click Search Button")
        except Exception as e:
            print(f"Error in click_search_button: {e}")

    def click_edit_button(self):
        logger.info(f"Inside Click Edit Button")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.click_edit)
            ).click()
            print("Edit button clicked successfully.")
            logger.info(f"Out from Click Edit Button")
        except Exception as e:
            print(f"Error in click_edit_button: {e}")

    def click_provider_button(self):
        logger.info(f"Inside Click Provider Button")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(normalize-space(), 'Providers')]"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()
            logger.info(f"Out from Click Provider Button")
        except Exception as e:
            print(f"Error in click_provider_button: {e}")

    def click_add_provider(self):
        logger.info(f"Inside Click Add Provider")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.add_provider)
            ).click()
            print("Add Provider button clicked successfully.")
            logger.info(f"Out from Click Add Peovider")
        except Exception:
            print("Error: Add Provider button is not clickable.")

    def enter_last_name(self, last_name):
        logger.info(f"Inside Enter Last Name :{last_name}")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.last_name1)
            ).send_keys(last_name)
            print(f"Last name entered successfully: {last_name}")
            logger.info(f"Out from Enter Last Name :{last_name}")
        except Exception as e:
            print(f"Error in enter_last_name while entering '{last_name}': {e}")

    def enter_first_name(self, first_name):
        logger.info(f"Inside Enter Last Name :{first_name}")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.first_name1)
            ).send_keys(first_name)
            print(f"Last name entered successfully: {first_name}")
            logger.info(f"Out from Enter Last Name :{first_name}")
        except Exception as e:
            print(f"Error in enter_last_name while entering '{first_name}': {e}")

    def enter_effective_date(self, value):
        logger.info(f"Inside Enter Effective Date:{value}")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.effective_date)
            ).send_keys(value)
            print(f"Effective date entered successfully: {value}")
            logger.info(f"Out from Enter Effective Date:{value}")
        except Exception as e:
            print(f"Error in enter_effective_date while entering '{value}': {e}")

    def select_contract_type1(self, value):
        logger.info(f"Inside Select Contract Type1:{value}")
        try:
            dropdown_element = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//select[@id='Rslt_ContractType']"))
            )
            Select(dropdown_element).select_by_visible_text(value)
            print(f"Contract type selected successfully: {value}")
            logger.info(f"Out from Select Contract Type1:{value}")
        except Exception as e:
            print(f"Error in select_contract_type1 while selecting '{value}': {e}")

    def select_primary_speciality_dropdown1(self, speciality_value: str):
        """Select speciality from dropdown based on given speciality value"""
        self.click(self.primary_specialist)

        # WebDriverWait(self.driver, 5).until(
        #     EC.presence_of_element_located(
        #         (By.XPATH, "//div[@id='Rslt_specialty_chosen']//ul[@class='chosen-results'][1]")
        #     )
        # )

        option_xpath = f"//div[@id='Rslt_specialty_chosen']//ul[@class='chosen-results']//li[contains(text(), '{speciality_value}')]"
        option = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, option_xpath))
        )
        option.click()

    def select_primary_speciality_dropdown2(self, network):
        try:
            wait = WebDriverWait(self.driver, 10)

            # Step 1: Map network to speciality
            speciality_value = constants.PRIMARY_SPECIALITY_MAP.get(network)
            if not speciality_value:
                raise ValueError(f"No mapping found for network '{network}'")

            # Step 2: Click to open the dropdown
            self.click(self.primary_specialist)

            # Step 3: Click the visible option from the Chosen dropdown
            option = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, f"//div[@id='Rslt_specialty_chosen']//ul[@class='chosen-results']/li[text()='{speciality_value}']")
                )
            )
            option.click()
            print(f"✅ Selected speciality: {speciality_value}")

        except Exception as e:
            print(f"❌ Error selecting primary speciality dropdown: {str(e)}")

    def select_payment_type1(self, value):
        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_PaymentType']"))
        dropdown.select_by_visible_text(value)

    def select_provider_type_dropdown1(self, category: str, network: str, speciality: str ):
        logger.info(
            f"Inside Select Provider Type Dropdown with category: {category}, network: {network}, speciality: {speciality}")
        try:
            dropdown_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "(//tbody/tr/td/select[@style='width:150px'])[3]"))
            )
            dropdown = Select(dropdown_element)

            # Get all available options as text
            options = [opt.text.strip() for opt in dropdown.options]
            value_to_select = None

            # Normalize inputs
            category = category.strip().upper() if category else ""
            network = network.strip().upper() if network else ""
            speciality = speciality.strip().upper() if speciality else ""

            # Case 1: Category is MD, DO, DPM
            if category in ["MD", "DO", "DPM"]:
                if network == "PODIATRY" and "PODIATRIST" in options:
                    value_to_select = "PODIATRIST"
                elif network == "ORTHOPEDICS" and "ORTHOPEDICS" in options:
                    value_to_select = "ORTHOPEDICS"
                elif network == "DERMATOLOGY":
                    if "MOHS" in speciality and "MOHS SURGEON AND GENERAL" in options:
                        value_to_select = "MOHS SURGEON AND GENERAL"
                    elif "GENERAL DERMATOLOGY" in options:
                        value_to_select = "GENERAL DERMATOLOGY"
                else:
                    if "SPECIALIST" in options:
                        value_to_select = "SPECIALIST"

            # Case 2: Any category that is NOT MD, DO, DPM
            else:
                if "PHYSICIAN EXTENDER" in options:
                    value_to_select = "PHYSICIAN EXTENDER"

            # Final selection
            if value_to_select:
                dropdown.select_by_visible_text(value_to_select)
                print(f"Provider type '{value_to_select}' selected successfully.")
                logger.info(f"Out from Select Provider Type Dropdown: {value_to_select}")
            else:
                print("No matching provider type found in dropdown.")
                logger.warning("Provider type not found in dropdown.")

        except Exception as e:
            print(f"Error selecting provider type: {e}")
            logger.error(f"Error selecting provider type: {e}")

    def select_account1(self, value):
        logger.info(f"Inside Select Account1:{value}")
        try:
            dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_AccountNo']"))
            dropdown.select_by_visible_text(value)
            print(f"Account selected successfully: {value}")
            logger.info(f"Outside from Select Account1:{value}")
        except Exception as e:
            print(f"Error in select_account1 while selecting '{value}': {e}")

    def select_template1(self, company_name: str):
        logger.info(f"Inside Select Template1:{company_name}")
        try:
            dropdown_value = TEMPLATE_MAP.get(company_name)

            if not dropdown_value:
                raise ValueError(f"No contract template mapping found for company: {company_name}")

            dropdown = Select(
                self.driver.find_element(By.XPATH, "//select[@id='Taslt_ContractTemplateID']")
            )
            dropdown.select_by_visible_text(dropdown_value)
            print(f"Template selected successfully for company '{company_name}': {dropdown_value}")
            logger.info(f"Out from Select Template1:{company_name}")

        except Exception as e:
            print(f"Error in select_template1 while selecting template for company '{company_name}': {e}")

    # def select_template1(self):
    #     dropdown = WebDriverWait(self.driver, 5).until(
    #         EC.presence_of_element_located((By.XPATH, "//select[@id='Taslt_ContractTemplateID']"))
    #     )
    #     select = Select(dropdown)
    #     select.select_by_value('271')

    def click_add_new_location(self):
        logger.info(f"Inside Click Add New Location")
        try:
            self.click(self.add_new_location)
            print("Add New Location button clicked successfully.")
            logger.info(f"Inside Click Add New Location")
        except Exception as e:
            print(f"Error in click_add_new_location: {e}")

    def enter_address2(self, value):
        logger.info(f"Inside Enter Address2:{value}")
        try:
            self.enter_text(self.address2, value)
            print(f"Address 2 entered successfully: {value}")
            logger.info(f"Out from Enter Address2:{value}")
        except Exception as e:
            print(f"Error in enter_address2 while entering '{value}': {e}")

    def enter_address_line2(self, value):
        logger.info(f"Inside Enter Address Line2:{value}")
        try:
            self.enter_text(self.address_line2, value)
            print(f"Address 2 entered successfully: {value}")
            logger.info(f"Out from Enter Address Line2:{value}")
        except Exception as e:
            print(f"Error in enter_address2 while entering '{value}': {e}")

    def enter_name1(self, value):
        logger.info(f"Inside Enter Name1:{value}")
        try:
            self.enter_text(self.name1, value)
            print(f"Name entered successfully: {value}")
            logger.info(f"Out from Enter Name1:{value}")
        except Exception as e:
            print(f"Error in enter_name1 while entering '{value}': {e}")

    def select_state1(self, value):
        logger.info(f"Inside Select State1:{value}")
        try:
            dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Taslt_state']"))
            dropdown.select_by_visible_text(value)
            print(f"State selected successfully: {value}")
            logger.info(f"Out from Select State1:{value}")
        except Exception as e:
            print(f"Error in select_state1 while selecting '{value}': {e}")

    def enter_zip1(self, value):
        logger.info(f"Inside Enter Zip1:{value}")
        try:
            self.enter_text(self.zip1, value)
            print(f"ZIP entered successfully: {value}")
            logger.info(f"Out from Enter Zip1:{value}")
        except Exception as e:
            print(f"Error in enter_zip1 while entering '{value}': {e}")

    def enter_city1(self, value):
        logger.info(f"Inside Enter City1:{value}")
        try:
            self.enter_text(self.city1, value)
            print(f"City entered successfully: {value}")
            logger.info(f"Out from Enter City1:{value}")
        except Exception as e:
            print(f"Error in enter_city1 while entering '{value}': {e}")

    def click_save1(self):
        logger.info(f"Inside Click Save1")
        try:
            # Wait until element is present and clickable
            element = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.save1)
            )

            try:
                element.click()  # normal Selenium click
                print("Save button clicked successfully.")
            except Exception:
                # fallback to JS click if normal click fails
                self.driver.execute_script("arguments[0].click();", element)
                print("Save button clicked successfully via JS.")

            # ✅ Handle potential alert after click
            self.handle_save_alert()
            return True
            logger.info(f"Out from Click Save1")

        except Exception as e:
            print(f"Error in click_save1: {e}")
            return False


    def handle_save_alert(self, timeout=5):
        """Handle alerts that appear after saving"""
        try:
            for i in range(timeout):
                try:
                    alert = self.driver.switch_to.alert
                    alert_text = alert.text
                    print(f"Alert detected: {alert_text}")

                    if "duplicate address" in alert_text.lower():
                        print("🔄 Duplicate address detected - accepting alert")
                        alert.accept()
                        return "duplicate"
                    elif "error" in alert_text.lower():
                        print("⚠️ Error alert detected - accepting")
                        alert.accept()
                        return "error"
                    else:
                        print("ℹ️ Other alert detected - accepting")
                        alert.accept()
                        return "other"

                except NoAlertPresentException:
                    time.sleep(1)
                    continue

            print("No alert appeared after save.")
            return None

        except Exception as e:
            print(f"Error handling save alert: {e}")
            return None

    def click_cancel1(self):
       self.click(self.cancel1)

    def check_npi_search_field(self):
        logger.info(f"Inside check NPI Search Field")
        """Check if NPI search field exists on the page"""
        try:
            # Ensure self.npi_fields is properly defined as (By.<METHOD>, "locator")
            if not hasattr(self, 'npi_fields') or not isinstance(self.npi_fields, tuple) or len(self.npi_fields) != 2:
                raise ValueError("npi_fields must be defined as a tuple (By.<METHOD>, 'locator')")

            # Wait for element to be present (not necessarily visible)
            elements = WebDriverWait(self.driver, 5).until(
                EC.presence_of_all_elements_located(self.npi_fields)
            )
            return len(elements) > 0
            logger.info(f"Out from check NPI Search Field")
        except TimeoutException:
            return False
        except NoSuchElementException:
            return False
        except Exception as e:
            print(f"Error checking NPI search field: {str(e)}")
            return False

    def choose_credentialing_tab1(self):
        try:
            self.wait_for_element_present(self.credentialing_tab)
            element = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.credentialing_tab1)
            )
            element.click()
        except Exception as e:
            print(f"<UNK> Failed to click credentialing tab: {e}")

    def select_speciality1(self, network):
        logger.info(f"Inside Select Speciality1:{network}")
        try:
            wait = WebDriverWait(self.driver, 10)

            # Step 1: Click the dropdown to open options
            self.click(self.primary_specialist1)

            # Step 2: Define option mapping
            option_map = {
                "podiatry": "//li[contains(normalize-space(), 'POD - PODIATRY')]",
                "dermatology": "//li[contains(normalize-space(), 'D - DERMATOLOGY')]",
                "orthopedic": "//li[contains(normalize-space(), 'ORT - ORTHOPEDICS')]",
                "pain management": "//li[contains(normalize-space(), 'APM - Anesthesiology/Pain Management')]",
                "podiatry, wound care": "//li[contains(normalize-space(), 'POD - PODIATRY')]",

            }

            # Step 3: Get correct xpath
            option_xpath = option_map.get(network)
            if not option_xpath:
                raise ValueError(f"No speciality mapping found for network: {network}")

            # Step 4: Wait for option to be visible and click
            option = wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
            option.click()
            print(f"✅ Selected speciality: {network}")
            logger.info(f"Out from Select Speciality1:{network}")
        except Exception as e:
            print(f"<UNK> Failed to click speciality: {str(e)}")

    def click_primary(self):
        logger.info(f"Inside Click Primary")
        try:
            self.click(self.primary)
            print("Primary button clicked successfully.")
            logger.info(f"Out from Click Primary")
        except Exception as e:
            print(f"Error in click_primary: {e}")

    def get_next_location_letter(driver):
        """Check existing locations and return next available letter"""
        existing_locations = driver.find_elements(By.XPATH, "//input[contains(@name, 'LOCATION') and @type='checkbox']")
        used_letters = []

        for loc in existing_locations:
            loc_name = loc.get_attribute("name")
            # Extract the letter part (assuming format like "LOCATION_A")
            letter = loc_name.split("_")[-1].upper()
            used_letters.append(letter)

        # Find next available letter starting from A
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter not in used_letters:
                return letter

        return "A"

    def provider_table_rows(self):
        logger.info(f"Inside Provider Table Rows")
        try:
            rows = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//tr[@onmouseover='QL_MOver(this)']"))
            )
            plan_data = []
            provider_id = None

            for inner_row in rows:
                try:
                    plan = inner_row.find_element(By.XPATH, "./td[2]").text.strip()
                    plan_data.append(plan)

                    # Get provider_id from API
                    provider_id = api.pr_site_data.RequestAPi.get_provider_id(plan_data)

                except Exception as e:
                    print(e)
                    continue

            return provider_id
            logger.info(f"Out from Provider Table Rows")

        except Exception as e:
            print(f"<UNK> Failed to click provider table row: {str(e)}")
            return None

    def enter_provider_letter(self, value):
        logger.info(f"Inside Enter Provider Letter:{value}")
        try:
            self.enter_text(self.provider_letter, value)
            print(f"Provider letter entered successfully: {value}")
            logger.info(f"Out from Enter Provider Letter:{value}")
        except Exception as e:
            print(f"Error in enter_provider_letter while entering '{value}': {e}")

    # def is_edit_button_available(self ):
    #     logger.info(f"Inside Check Edit Button is Available or Not")
    #     try:
    #         WebDriverWait(self.driver, 5).until(
    #             EC.presence_of_element_located((By.XPATH, "//img[@title='Edit']"))
    #         )
    #         return True
    #         logger.info(f"Out from Check Edit Button is Available or Not")
    #     except TimeoutException as e:
    #         print(f" TimeoutException: {e}")
    #         return False
    #     except Exception as e:
    #         print(f" Unexpected error while checking Edit button: {e}")
    #         return False
    def is_edit_button_available(self, retries=3, wait_time=5):
        logger.info(f"Inside Check Edit Button is Available or Not")

        for attempt in range(retries):
            try:
                WebDriverWait(self.driver, wait_time).until(
                    EC.presence_of_element_located((By.XPATH, "//img[@title='Edit']"))
                )
                print(f"✅ Edit button found on attempt {attempt + 1}")
                return True
            except Exception as e:
                print(f" Attempt {attempt + 1}: Edit button not found ({type(e).__name__})")
                if attempt < retries - 1:
                    time.sleep(2)
                logger.info(f"Out from Check Edit Button is Available or Not")

        print("Edit button not available after retries")
        return False

    def click_edit_for_healthplan(self, provider_id: str):
        logger.info(f"Inside Click Edit Button for Provider ID ending with: {provider_id}")
        try:
            # ✅ Extract last letter from provider_id (inside brackets)
            if "(" in provider_id and ")" in provider_id:
                target_letter = provider_id.split("(")[-1].strip(")")
            else:
                target_letter = provider_id  # Use the letter directly if no brackets

            logger.info(f"Looking for Provider IDs ending with ({target_letter})")

            # Wait for rows
            rows = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//tr[@onmouseover='QL_MOver(this)']"))
            )

            matching_rows = []  # Store all matching rows

            for row in rows:
                try:
                    provider_id_text = row.find_element(By.XPATH, "./td[2]").text.strip()
                    logger.info(f"Checking row Provider ID: {provider_id_text}")

                    if provider_id_text.endswith(f"({target_letter})"):
                        logger.info(f"✅ Found matching provider row: {provider_id_text}")
                        matching_rows.append(row)  # Add matching row to list

                except Exception as inner_e:
                    logger.warning(f"Skipping row due to error: {inner_e}")
                    continue

            if matching_rows:
                # Get the last matching row
                last_matching_row = matching_rows[-1]
                provider_id_text = last_matching_row.find_element(By.XPATH, "./td[2]").text.strip()
                logger.info(f"🔄 Clicking Edit for LAST matching Provider ID: {provider_id_text}")

                edit_btn = last_matching_row.find_element(By.XPATH, ".//img[@title='Edit']")
                self.driver.execute_script("arguments[0].scrollIntoView(true);", edit_btn)
                self.driver.execute_script("arguments[0].click();", edit_btn)  # safer click
                logger.info("Clicked Edit Button successfully")
                return True
            else:
                logger.error(f"No Provider ID found in table ending with ({target_letter})")
                return False

        except Exception as e:
            logger.error(f"Error in click_edit_for_healthplan: {e}")
            return False

    def click_healthplan_panel(self):
        logger.info(f"Inside Click Health Plan Panel")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//input[@value='Health Plan Panel']"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()
            logger.info(f"Out from Click Health Plan Panel")
        except Exception as e:
            print(f"Error in click_healthplan_panel: {e}")

    def select_taxonomy(self, value):
        logger.info(f"Inside Select Taxonomy:{value}")
        try:
            dropdown = Select(self.driver.find_element(By.XPATH, "(//tbody/tr/td/select[@style='width:250px;'])[last()]"))
            dropdown.select_by_visible_text(value)
            print(f"Taxonomy selected successfully: {value}")
            logger.info(f"Outside from Select Account1:{value}")
        except Exception as e:
            print(f"Error in select_taxonomy while selecting '{value}': {e}")

    def enter_membership_date(self, value):
        logger.info(f"Inside Enter Membership Start Date:{value}")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.membership_start_date)
            ).send_keys(value)
            print(f"Effective date entered successfully: {value}")
            logger.info(f"Out from Enter Membership Start Date:{value}")
        except Exception as e:
            print(f"Error in enter_membership_start_date while entering '{value}': {e}")

    def click_plus_button(self):
        logger.info(f"Inside Click Plus Button")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(self.click_plus)
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()
            logger.info(f"Out from Click Plus Button")
        except Exception as e:
            print(f"Error in click_plus_button: {e}")

    def click_save_healthplan(self):
        logger.info("Inside Click Save Health Plan")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(self.save_healthplan)
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()
            logger.info("Save Health Plan clicked")

            try:
                WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                alert = self.driver.switch_to.alert
                logger.info(f"Alert text: {alert.text}")
                alert.accept()
                logger.info("Alert accepted successfully")
            except TimeoutException:
                logger.info("No alert appeared after clicking Save")

            logger.info("Out from Click Save Health Plan")
        except Exception as e:
            print(f"Error in click_save_healthplan: {e}")

    def click_other_ids(self):
        logger.info(f"Inside Click Other IDs")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(self.other_ids)
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()
            logger.info(f"Out from Click Other IDs")
        except Exception as e:
            print(f"Error in click_other_ids: {e}")

    def click_add_plus(self):
        logger.info(f"Inside Click Add Plus")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(self.add_plus)
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()
            logger.info(f"Out from Click Add Plus")
        except Exception as e:
            print(f"Error in click_add_plus: {e}")

    def click_provider_id(self, provider_id: str):
        logger.info("Inside Click Provider ID")
        try:
            dropdown_element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(self.provider_id_dropdown)
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", dropdown_element)

            select = Select(dropdown_element)

            last_letter = provider_id.strip()[-1] if provider_id else '(A)'
            if not last_letter:
                logger.error("Target provider_id is empty")
                return False

            matched = False
            for option in select.options:
                option_text = option.text.strip()
                if option_text.endswith(f"({last_letter})"):
                    select.select_by_visible_text(option_text)
                    logger.info(f"Selected Provider ID from dropdown: {option_text}")
                    matched = True
                    break

            if not matched:
                logger.warning(f"No Provider ID matched with last letter: {last_letter}")
                return False

            logger.info("Out from Click Provider ID")
            return True

        except Exception as e:
            print(f"Error in click_provider_id: {e}")
            return False

    def enter_taxonomy_code(self, value):
        logger.info(f"Inside Enter Taxonomy Code:{value}")
        try:
            self.enter_text(self.taxonomy_no, value)
            print(f"Date entered successfully: {value}")
            logger.info(f"Out from Enter Taxonomy Code:{value}")
        except Exception as e:
            print(f"Error in enter_taxonomy_code while entering '{value}': {e}")

    def click_save_taxonomy(self):
        logger.info("Inside Click Save Taxonomy")
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located(self.save_taxonomy)
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()
            logger.info("Save Taxonomy button clicked")

            try:
                WebDriverWait(self.driver, 5).until(EC.alert_is_present())
                alert = self.driver.switch_to.alert
                logger.info(f"Alert found with text: {alert.text}")
                alert.accept()
                logger.info("Alert accepted successfully")
            except Exception:
                logger.info("No alert appeared after clicking Save Taxonomy")

            logger.info("Out from Click Save Taxonomy")

        except Exception as e:
            print(f"Error in click_save_taxonomy: {e}")

    def click_edit_for_healthplan_for_A(self):
        logger.info("Inside Click Edit Button for Healthplan (looking for IDs ending with 'A')")
        try:
            rows = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//tr[@onmouseover='QL_MOver(this)']"))
            )

            for row in rows:
                try:
                    provider_id_text = row.find_element(By.XPATH, "./td[2]").text.strip()

                    if provider_id_text and provider_id_text.endswith("(A)"):
                        logger.info(f"Found matching provider row: {provider_id_text}")
                        edit_btn = row.find_element(By.XPATH, ".//img[@title='Edit']")
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", edit_btn)
                        edit_btn.click()
                        logger.info("Clicked Edit Button successfully")
                        return True

                except Exception as inner_e:
                    logger.warning(f"Skipping row due to error: {inner_e}")
                    continue

            logger.error("No provider ID found in table ending with 'A'")
            return False

        except Exception as e:
            print(f"Error in click_edit_for_healthplan_for_A: {e}")
            return False

    def click_provider_id_for_A(self):
        try:
            # Step 1: Locate the select element
            select_element = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//tbody/tr/td/select[contains(@name,'new_provider_id')]"))
            )

            # Step 2: Wrap it with Select
            select = Select(select_element)

            # Step 3: Loop through options to find one ending with (A)
            for option in select.options:
                text = option.text.strip()
                if text.endswith("(A)"):
                    select.select_by_visible_text(text)
                    print(f"✅ Selected NPI: {text}")
                    return True

            print("⚠️ No NPI ending with (A) found.")
            return False

        except Exception as e:
            print(f"❌ Error in select_npi_ending_with_A: {e}")
            return False














