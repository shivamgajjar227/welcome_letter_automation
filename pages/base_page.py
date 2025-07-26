import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class BasePage:
    def __init__(self, driver):
        self.new_window = None
        self.main_window = None
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 20)

    def click(self, locator):
        self.driver.find_element(*locator).click()

    def enter_text(self, locator, text):
        self.driver.find_element(*locator).clear()
        self.driver.find_element(*locator).send_keys(text)

    def switch_to_new_window(self):
        time.sleep(1)
        self.main_window = self.driver.current_window_handle  # ✅ Store current window
        handles = self.driver.window_handles
        for handle in handles:
            if handle != self.main_window:
                self.driver.switch_to.window(handle)
                break

    def switch_back_to_main(self):
        if not self.main_window:
            raise Exception("Main window handle is not set. Did you call switch_to_new_window first?")
        self.driver.switch_to.window(self.main_window)

    def select_value_from_dropdown(self, locator,value):
        dropdown = Select(self.driver.find_element(By.XPATH, *locator))
        dropdown.select_by_value(value)

    def wait_for_element_present(self, locator, timeout=10):
        return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(locator))

