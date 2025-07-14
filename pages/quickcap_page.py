from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from pages.base_page import BasePage

class QuickcapPage(BasePage):

    USERNAME_FIELD = (By.XPATH, "//input[@id='TaRtxt_username']")
    PASSWORD_FIELD = (By.XPATH, "//input[@id='TaRpas_password']")
    LOGIN_BUTTON = (By.XPATH, "//input[@value='LOGIN']")
    select_company = (By.XPATH, "//td[@class='clientBold']//a[@id='comptda_DNSHUMANA']")
    credentialing_tab = (By.XPATH, "(//h3[normalize-space()='Credentialing'])[1]")
    practitioner_data = (By.XPATH, "//a[normalize-space()='Practitioner Data']")
    npi_fields = (By.XPATH, "//input[@id='Sr_Tatxt_npi']")
    quick_add_button = (By.CSS_SELECTOR, "input[value='Quick Add']")
    categories_drowpdown = (By.XPATH, "//select[@id='Rslt_prac_category']")
    quick_add_window_npi_button = (By.XPATH, "//input[@id='TaRtxt_npi_number']")
    select_provider_type = (By.XPATH, "//select[@id='Rslt_provider_type']")
    provide_id_field = (By.XPATH, "//input[@id='TaRtxt_provider_id']")



    def login(self, username, password):
        self.enter_text(self.USERNAME_FIELD, username)
        self.enter_text(self.PASSWORD_FIELD, password)
        self.click(self.LOGIN_BUTTON)

    def choose_company(self):
        self.click(self.select_company)

    def choose_credentialing_tab(self):
        self.click(self.credentialing_tab)

    def select_value_from_dropdown(self, locator,value):
        dropdown = Select(self.driver.find_element(By.XPATH, locator))
        dropdown.select_by_value(value)

    def choose_practitioner_data(self):
        self.click(self.practitioner_data)

    def enter_npi(self, npi):
        self.click(self.npi_fields)
        self.enter_text(self.npi_fields, npi)

    def click_quick_add_button(self):
        self.click(self.quick_add_button)

    def select_category_dropdown(self, value):

        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_prac_category']"))
        dropdown.select_by_visible_text(value)
        # self.click(self.categories_drowpdown)

    def click_quick_add_window_npi_button(self, npi):
        self.click(self.quick_add_window_npi_button)
        self.enter_text(self.quick_add_window_npi_button, npi)

    def select_provider_type_dropdown(self, value):

        dropdown = Select(self.driver.find_element(By.XPATH, "//select[@id='Rslt_provider_type']"))
        dropdown.select_by_visible_text(value)

    def enter_provider_id(self, value):
        self.enter_text(self.provide_id_field, value)

    def select_primary_speciality_dropdown(self, value):

        self.select_value_from_dropdown(self., value)





