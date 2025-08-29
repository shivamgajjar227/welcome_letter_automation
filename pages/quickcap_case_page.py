import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pages.base_page import BasePage
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.common.exceptions import TimeoutException


class QuickcapCasePage(BasePage):

    USERNAME_FIELD = (By.XPATH, "//input[@id='TaRtxt_username']")
    PASSWORD_FIELD = (By.XPATH, "//input[@id='TaRpas_password']")
    LOGIN_BUTTON = (By.XPATH, "//input[@value='LOGIN']")
    select_company = (By.XPATH, "//td[@class='clientBold']//a[@id='comptda_DNSF']")
    credentialing_tab = (By.XPATH, "(//h3[normalize-space()='Credentialing'])[1]")
    practitioner_data = (By.XPATH, "//a[normalize-space()='Practitioner Data']")
    change_company = (By.XPATH, "//a[normalize-space()='Change Company']")
    companys = (By.XPATH, "//tbody")
    submit = (By.XPATH, "//input[@id='btnSumit']")
    image = (By.XPATH, "//body/table[1]/tbody/tr[2]/td[1]/table[1]")
    company_1= (By.XPATH, "(//img[@title='Log-in'])[1]")
    username_in_company_prompt = (By.XPATH, "//input[@id='username']")
    password_in_company_prompt = (By.XPATH, "(//input[@id='userpass'])[1]")
    login_button_in_company_prompt = (By.XPATH, "//input[@id='btnSumit']")

    def login(self, username, password):
        self.enter_text(self.USERNAME_FIELD, username)
        self.enter_text(self.PASSWORD_FIELD, password)
        self.click(self.LOGIN_BUTTON)


    def loginn(self, username, password):
        self.enter_text(self.USERNAME_FIELD, username)
        self.enter_text(self.PASSWORD_FIELD, password)
        self.click(self.submit)

    # def select_company_from_dropdown(self, value):
    #     dropdown = Select(self.driver.find_element(By.XPATH, "//td[@class='clientBold']//a[@id='comptda_DNSF']"))
    #     dropdown.select_by_visible_text(value)

    def click_company(self):
        self.click(self.select_company)

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

    def choose_credentialing_tab(self):
        # self.wait_for_element_present(self.credentialing_tab)
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.credentialing_tab)
        ).click()

    def choose_practitioner_data(self):
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.practitioner_data)
        ).click()

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

    def choose_company(self, company_name):
        """Simple function to select a company by name"""
        try:
            # Wait for and click the company element
            company = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), '{company_name}')]"))
            )
            company.click()
            print(f"Successfully selected: {company_name}")
            return True

        except Exception as e:
            print(f"Failed to select company: {str(e)}")
            return False

    def click_one_company(self, value):
        self.click(self.companys)

    def select_company_1(self):
        self.click(self.company_1)

    def enter_username_in_company_prompt(self, value):
        self.enter_text(self.username_in_company_prompt, value)

    def enter_password_in_company_prompt(self, value):
        self.enter_text(self.password_in_company_prompt, value)

    def click_login_button_in_company_prompt(self):
        self.click(self.login_button_in_company_prompt)

    def get_company_xpath(self, company_code):
        image_path = f"./../general/images/fancy/{company_code}.gif"
        self.driver.find_element(By.XPATH,f'//a[@onclick="showLogin(\'{company_code}\', \'{company_code}\', \'{image_path}\');"]//img[@title="Log-in"]').click()

    def driver_close(self):
        self.driver.quit()