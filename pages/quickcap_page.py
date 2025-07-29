import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pages.base_page import BasePage
from selenium.common.exceptions import TimeoutException


class QuickcapPage(BasePage):

    USERNAME_FIELD = (By.XPATH, "//input[@id='TaRtxt_username']")
    PASSWORD_FIELD = (By.XPATH, "//input[@id='TaRpas_password']")
    LOGIN_BUTTON = (By.XPATH, "//input[@value='LOGIN']")
    select_company = (By.CSS_SELECTOR, "table[width='100%'][cellspacing='10']")
    credentialing_tab = (By.XPATH, "(//h3[normalize-space()='Credentialing'])[1]")
    practitioner_data = (By.XPATH, "//a[normalize-space()='Practitioner Data']")
    npi_fields = (By.XPATH, "//input[@id='Sr_Tatxt_npi']")
    quick_add_button = (By.CSS_SELECTOR, "input[value='Quick Add']")
    categories_drowpdown = (By.XPATH, "//select[@id='Rslt_prac_category']")
    quick_add_window_npi_button = (By.XPATH, "//input[@id='TaRtxt_npi_number']")
    select_provider_type = (By.XPATH, "//select[@id='Rslt_provider_type']")
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
    close = (By.XPATH, "//iframe[@id='TB_iframeContent']")


    def login(self, username, password):
        self.enter_text(self.USERNAME_FIELD, username)
        self.enter_text(self.PASSWORD_FIELD, password)
        self.click(self.LOGIN_BUTTON)

    def choose_company(self,company_name):
        print(f"🔍 Trying to click on company: {company_name}")
        company_tab = WebDriverWait(self.driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, f"//*[contains(text(), '{company_name}')]"))
        )
        company_tab.click()

    def choose_credentialing_tab(self):
        # self.wait_for_element_present(self.credentialing_tab)
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.credentialing_tab)
        ).click()

    def choose_practitioner_data(self):
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.practitioner_data)
        ).click()

    def enter_npi(self, npi):
        self.click(self.npi_fields)
        self.enter_text(self.npi_fields, npi)

    def click_quick_add_button(self):
        quick_add_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//input[@value='Quick Add']"))
        )
        quick_add_btn.click()

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

    def select_provider_type_dropdown(self, value):

        select_element = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//select[@id='Rslt_provider_type']"))
        )
        dropdown = Select(select_element)
        dropdown.select_by_visible_text(value)

    def enter_provider_id(self, value):
        field = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.provide_id_field)
        )
        field.clear()
        field.send_keys(value)

    def select_primary_speciality_dropdown(self, value):
        self.click(self.primary_specialist)
        time.sleep(2)
        self.driver.find_element(By.XPATH, f"//li[normalize-space()='{value}']").click()

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

    def switch_to_new_window(self):
        time.sleep(1)
        handles = self.driver.window_handles
        self.driver.switch_to.window(handles[-1])  # switch to latest opened window

    def switch_to_previous_window(self):
        handles = self.driver.window_handles
        self.driver.switch_to.window(handles[1])  # or save quick_add_window if needed

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
        self.click(self.search_npi)

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

    def click_agree(self):
        self.click(self.agree)

    def click_cancel(self):
        WebDriverWait(self.driver, 10).until(
            EC.invisibility_of_element((By.ID, "TB_overlay"))
        )
        self.click(self.close)



0








