import time

from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage

class SqlServerPage(BasePage):

    npi_search = (By. CSS_SELECTOR, "#ReportViewerControl_ctl04_ctl03_txtValue")
    report_view = (By.CSS_SELECTOR, "#ReportViewerControl_ctl04_ctl00")
    credentialing = (By.XPATH, "//span[contains(text(),'Credentialing')]")
    provider_report = (By.XPATH, "//span[contains(text(),'Provider Reports')]")
    pml_report = (By.XPATH, "//span[contains(text(),'AHCA PML Report')]")
    address = (By.XPATH, "//div[contains(text(), 'Prov Serv Loc Address Line1')]/following::td[1]//div[@id]")

    def click_credential(self):
        element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(self.credentialing)
        )
        element.click()

    def click_provider_report(self):
        element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(self.provider_report)
        )
        element.click()

    def click_pml_report(self):
        element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(self.pml_report)
        )
        element.click()

    def click_npi_search(self):
        element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(self.npi_search)
        )
        element.click()

    def enter_npi_search(self, value):
        input_box = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.npi_search)
        )
        input_box.clear()
        input_box.send_keys(value)

    def click_report_view(self):
        element = WebDriverWait(self.driver, 5).until(
            EC.element_to_be_clickable(self.report_view)
        )
        element.click()

    def switch_to_report_iframe(self):
        iframe = WebDriverWait(self.driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//iframe[@title='Report Viewer']"))
        )
        self.driver.switch_to.frame(iframe)

    def get_address(self):
        try:
            address_xpath = (By.XPATH, "/html[1]/body[1]/form[1]/table[1]/tbody[1]/tr[1]/td[1]/div[2]/div[1]/table[1]/tbody[1]/tr[5]/td[3]/div[1]/div[1]/div[1]/table[1]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[2]/td[1]/table[1]/tbody[1]/tr[1]/td[1]/table[1]/tbody[1]/tr[3]/td[8]/div[1]/div[1]")
            address_elem = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(address_xpath)
            )
            return address_elem.text.strip()
        except (TimeoutException, NoSuchElementException):
            print("Address not found")
            return None

    def enter_group_npi_search(self, value):
        input_box = WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located(self.npi_search)
        )
        input_box.clear()
        input_box.send_keys(value)








