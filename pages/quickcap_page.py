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
    effective_date = (By.XPATH, "//input[@id='DtRtxt_ActiveFromDate']")
    primary_speciality = (By.XPATH, "//a[@class='chosen-single chosen-default trackAtt']")
    provider_type1 = (By.XPATH, "//option[normalize-space()='HDO']")
    add_new_location = (By.XPATH, "//input[@id='chk_add_new_location']")
    name1 = (By.XPATH, "//input[@id='Tatxt_LocationName']")
    address2 = (By.CSS_SELECTOR, "#Tatxt_Address1")
    zip1 = (By.CSS_SELECTOR, "#Tatxt_zip")
    city1 = (By.XPATH, "//input[@id='Tatxt_city']")
    save1 = (By.XPATH, "//input[@id='btn_submit']")
    cancel1 = (By.XPATH, "//input[@value='Cancel']")
    credentialing_tab1 = (By.XPATH, "(//h3[normalize-space()='Credentialing'])[1]")
    primary = (By.XPATH, "//input[@id='check_location_NEW_OFFICE_1']")
    provider_letter = (By.XPATH, "//input[@id='provider_id_suffix']")
    no_data_find = (By.XPATH, "//td[normalize-space()='No data found']")
    primary_specialist1 =  (By.XPATH,"//div[@id='Rslt_PrimarySpecialty_chosen']/a")



    def login(self, username, password):
        self.enter_text(self.USERNAME_FIELD, username)
        self.enter_text(self.PASSWORD_FIELD, password)
        self.click(self.LOGIN_BUTTON)

    def choose_company(self, company_name):
        print(f"🔍 Attempting to click login icon for: {company_name}")

        try:
            # STEP 1 — Check the currently selected company
            try:
                if company_name == "ONS Humana":
                    company_name = company_name.upper()
                current_company = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//span[@class='lbl-data']"  # Change this locator if your current company element is different
                    ))
                ).text.strip()

                print(f"ℹ️ Current company: {current_company}")

                if current_company.lower() == company_name.lower():
                    print(f"✅ '{company_name}' is already selected — skipping change.")
                    # Close popup and return
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return True
            except Exception as e:
                print(e)

            # STEP 2 — Wait for the login icon for the target company
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
            return True

        except Exception as e:
            print(f"❌ Failed to click login icon for '{company_name}': {e}")
            self.driver.save_screenshot(f"error_login_icon_{company_name.replace(' ', '_')}.png")
            return False

    def choose_credentialing_tab(self):

        # self.wait_for_element_present(self.credentialing_tab)
        try:
            element = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.credentialing_tab)
            )
            element.click()
        except Exception as e:
            print(f"<UNK> Failed to click credentialing tab: {e}")


    def choose_practitioner_data(self):
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.practitioner_data)
        ).click()

    def enter_npi(self, npi):
        self.click(self.npi_fields)
        self.enter_text(self.npi_fields, npi)

    def accept_alert(self, timeout=5):
        """
        Waits for alert up to `timeout` seconds and clicks OK if present.
        """
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

    def click_credential_button(self):
        try:
            quick_add_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//tbody/tr/td/input[@value='Credential ']"))
            )
            quick_add_btn.click()
            print("✅ Quick Add button clicked successfully.")
        except TimeoutException:
            print("❌ Quick Add button not found within the timeout.")
        except NoSuchElementException:
            print("❌ Quick Add button element does not exist on the page.")
        except ElementClickInterceptedException:
            print("⚠️ Quick Add button found but not clickable (another element is overlapping).")
        except Exception as e:
            print(f"⚠️ Unexpected error while clicking Quick Add button: {e}")

    def check_no_data_found_text(self):
        try:
            get_no_data_found_text = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//td[normalize-space()='No data found']"))
            ).text.strip()
            return get_no_data_found_text
        except Exception as e:
            print(f"⚠️ Unexpected error while clicking Quick Add button: {e}")

    def dismiss_alert(self, timeout=5):
        """
        Waits for alert up to `timeout` seconds and clicks Cancel if present.
        """
        for _ in range(timeout):
            try:
                alert = self.driver.switch_to.alert
                print("Alert text:", alert.text)  # optional
                alert.dismiss()  # ✅ Click Cancel
                print("Alert dismissed (Cancel clicked).")
                return True
            except NoAlertPresentException:
                time.sleep(1)
        print("No alert appeared.")
        return False


    def click_quick_add_button(self):
        try:
            quick_add_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//tbody/tr/td/input[@value='Quick Add']"))
            )
            quick_add_btn.click()
            print("✅ Quick Add button clicked successfully.")
        except TimeoutException:
            print("❌ Quick Add button not found within the timeout.")
        except NoSuchElementException:
            print("❌ Quick Add button element does not exist on the page.")
        except ElementClickInterceptedException:
            print("⚠️ Quick Add button found but not clickable (another element is overlapping).")
        except Exception as e:
            print(f"⚠️ Unexpected error while clicking Quick Add button: {e}")

    def select_category_dropdown(self, value):

        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_prac_category']"))
        dropdown.select_by_visible_text(value)
        # self.click(self.categories_drowpdown)

    def click_quick_add_window_npi_button(self, npi):
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.quick_add_window_npi_button)
        ).click()
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.quick_add_window_npi_button)
        ).send_keys(npi)

    def select_provider_type_dropdown(self):
        self.click(self.select_provider_type)
        time.sleep(2)
        self.driver.find_element(By.XPATH,"(//select[@id='Rslt_provider_type']/option)[3]").click()

    def enter_provider_id(self, value):
        field = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.provide_id_field)
        )
        field.clear()
        field.send_keys(value)

    def select_primary_speciality_dropdown(self, network_value):
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

        except Exception as e:
            print(f"❌ Dropdown selection failed: {str(e)}")

    def enter_last_first_name(self, last_name, first_name):
        self.enter_text(self.last_name, last_name)
        self.enter_text(self.first_name, first_name)

    def select_gender(self, value):
        dropdown_element = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//select[@id='Taslt_sex']"))
        )
        Select(dropdown_element).select_by_visible_text(value)

    def enter_birthdate(self, value):
        self.enter_text(self.birthdate, value)

    def select_contract_type(self, value):
        dropdown_element = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//select[@id='Rslt_contract_type']"))
        )
        Select(dropdown_element).select_by_visible_text(value)

    def enter_contract_from_date(self, value):
        self.enter_text(self.contract_from_date, value)

    def select_payment_type(self, value):
        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_PaymentType']"))
        dropdown.select_by_visible_text(value)

    def select_account(self, value):
        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_AccountNo']"))
        dropdown.select_by_visible_text(value)

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
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.organization)
        ).click()

    def enter_npi_org(self, value):
        self.enter_text(self.npi_org, value)

    def click_search_npi(self):
        element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(self.search_npi)
        )
        element.click()

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
        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_practice_type']"))
        dropdown.select_by_visible_text(value)

    def enter_name(self, value):
        self.enter_text(self.name, value)

    def enter_address1(self, value):
        self.enter_text(self.address1, value)

    def enter_city(self, value):
        self.enter_text(self.city, value)

    def select_state(self, value):
        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_state']"))
        dropdown.select_by_visible_text(value)

    def enter_zip(self, value):
        self.enter_text(self.zip, value)

    def click_save(self):
        self.click(self.save)

    def select_speciality(self, network):
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

    def click_org_id(self,  npi_number: str, address_line1: str):
        db: Session = SessionLocal()

        try:
            element = WebDriverWait(self.driver, 3).until(
                EC.element_to_be_clickable(self.org_id)
            )
            element.click()
            print("Organization ID clicked successfully")
            return True

        except Exception as e:
            error_message = f"Organization ID not found or clickable"
            print(error_message)

            # Save only the error in DB (do not update the 'update' column)
            db.query(NPIAddress).filter(
                NPIAddress.address_line1 == address_line1,
                NPIAddress.npi == npi_number
            ).update(
                {"remarks": error_message}
            )
            db.commit()
            return False

    def ensure_credentialing_tab(self):
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
        except Exception as e:
            print(f"Error ensuring Credentialing tab: {e}")
            return False


    def select_contract_template(self, company_name : str):
        dropdown_value = TEMPLATE_MAP.get(company_name)

        if not dropdown_value:
            raise ValueError(f"No contract template mapping found for company: {company_name}")

        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='slt_CONTRACT_TEMPLATE_ID']"))
        dropdown.select_by_visible_text(dropdown_value)

    def click_change_company(self):
        try:
            change_company_button = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.change_company)
            )
            change_company_button.click()
        except Exception as e:
            print(f"Error: {e}")
            print("Current URL:", self.driver.current_url)
            print("Title:", self.driver.title)
            self.driver.save_screenshot("change_company_error.png")
            raise

    def enter_username_in_company_prompt(self, value):
        self.enter_text(self.username_in_company_prompt, value)

    def enter_password_in_company_prompt(self, value):
        self.enter_text(self.password_in_company_prompt, value)

    def click_login_button_in_company_prompt(self):
        element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(self.login_button_in_company_prompt)
        )
        element.click()

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
        self.click(self.select_company)

    def click_search_button(self):
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.click_search)
        ).click()

    def click_edit_button(self):
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((self.click_edit))
        ).click()

    def click_provider_button(self):
        try:
            element = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(normalize-space(), 'Providers')]"))
            )
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            element.click()
        except Exception as e:
            raise e

    def click_add_provider(self):
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.add_provider)
        ).click()

    def enter_last_name(self, last_name1):
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.last_name1)
        ).send_keys(last_name1)

    def enter_effective_date(self, value):
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.effective_date)
        ).send_keys(value)

    def select_contract_type1(self, value):
        dropdown_element = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//select[@id='Rslt_ContractType']"))
        )
        Select(dropdown_element).select_by_visible_text(value)

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

    def select_provider_type_dropdown1(self):
        self.click(self.provider_type1)
        time.sleep(2)
        self.driver.find_element(By.XPATH,"//option[normalize-space()='HDO']").click()

    def select_account1(self, value):
        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_AccountNo']"))
        dropdown.select_by_visible_text(value)

    def select_template1(self, company_name: str):
        dropdown_value = TEMPLATE_MAP.get(company_name)

        if not dropdown_value:
            raise ValueError(f"No contract template mapping found for company: {company_name}")

        dropdown = Select(self.driver.find_element(By.XPATH, "// select[ @ id = 'Taslt_ContractTemplateID']"))
        dropdown.select_by_visible_text(dropdown_value)

    # def select_template1(self):
    #     dropdown = WebDriverWait(self.driver, 5).until(
    #         EC.presence_of_element_located((By.XPATH, "//select[@id='Taslt_ContractTemplateID']"))
    #     )
    #     select = Select(dropdown)
    #     select.select_by_value('271')

    def click_add_new_location(self):
       self.click(self.add_new_location)

    def enter_address2(self, value):
        self.enter_text(self.address2, value)

    def enter_name1(self, value):
        self.enter_text(self.name1, value)

    def select_state1(self, value):
        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Taslt_state']"))
        dropdown.select_by_visible_text(value)

    def enter_zip1(self, value):
        self.enter_text(self.zip1, value)

    def enter_city1(self, value):
        self.enter_text(self.city1, value)

    def click_save1(self):
       self.click(self.save1)

    def click_cancel1(self):
       self.click(self.cancel1)

    def check_npi_search_field(self):
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
            }

            # Step 3: Get correct xpath
            option_xpath = option_map.get(network)
            if not option_xpath:
                raise ValueError(f"No speciality mapping found for network: {network}")

            # Step 4: Wait for option to be visible and click
            option = wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
            option.click()
            print(f"✅ Selected speciality: {network}")
        except Exception as e:
            print(f"<UNK> Failed to click speciality: {str(e)}")

    def click_primary(self):
        self.click(self.primary)

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

        except Exception as e:
            print(f"<UNK> Failed to click provider table row: {str(e)}")
            return None

    def enter_provider_letter(self, value):
        self.enter_text(self.provider_letter, value)














