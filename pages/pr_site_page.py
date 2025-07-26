import time

from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage

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
    city = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Medical_Info_lblCity")
    state = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Medical_Info_lblState")
    zip_code = (By.CSS_SELECTOR, "#ctl00_MainContent_fm_Prov_Medical_Info_lblZipCode")


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
        sub_menu.click()




    def enter_npi_search(self, value):
        self.enter_text(self.npi_search, value)
        time.sleep(5)
        dropdown_options = WebDriverWait(self.driver, 10).until(
            EC.presence_of_all_elements_located(self.npi_search_dropdown)
        )
        for options in dropdown_options:
            if value in options.text:
                options.click()
                break
        self.click(self.search_button)

    def click_search_npi(self):
        self.click(self.search_button)

    def get_project_type(self):
        return self.driver.find_element(*self.project_type).text.strip()

    def get_individual_npi(self):
        return self.driver.find_element(*self.individual_npi).text.strip()

    def get_last_name(self):
        return self.driver.find_element(*self.last_name).text.strip()

    def get_first_name(self):
        return self.driver.find_element(*self.first_name).text.strip()

    def get_gender(self):
        return self.driver.find_element(*self.gender).text.strip()

    def get_city(self):
        return self.driver.find_element(*self.city).text.strip()

    def get_state(self):
        return self.driver.find_element(*self.state).text.strip()

    def get_zip_code(self):
        return self.driver.find_element(*self.zip_code).text.strip()









