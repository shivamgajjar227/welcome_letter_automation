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

    # def switch_to_new_window(self):
    #     time.sleep(1)
    #     self.main_window = self.driver.current_window_handle  # ✅ Store current window
    #     handles = self.driver.window_handles
    #     for handle in handles:
    #         if handle != self.main_window:
    #             self.driver.switch_to.window(handle)
    #             break

    def switch_to_new_window1(self):
        time.sleep(1)
        handles = self.driver.window_handles
        if len(handles) > 1:
            self.driver.switch_to.window(handles[-1])
        else:
            self.driver.switch_to.window(handles[0])

    def store_main_window(self):
        """Call this once after driver opens the initial main page."""
        self.main_window = self.driver.current_window_handle

    def switch_to_new_window(self):
        """Switch to the first window that is not the main window."""
        handles = self.driver.window_handles
        for h in handles:
            if h != self.main_window:
                self.driver.switch_to.window(h)
                return
        print("[WARN] No popup window found to switch to.")

    def switch_to_main(self):
        """Switch back to the main window."""
        if self.main_window and self.main_window in self.driver.window_handles:
            self.driver.switch_to.window(self.main_window)
        else:
            print("[ERROR] Main window handle not found in current handles.")


    def switch_back_to_main(self):
        if not self.main_window:
            raise Exception("Main window handle is not set. Did you call switch_to_new_window first?")
        self.driver.switch_to.window(self.main_window)

    def select_value_from_dropdown(self, locator,value):
        dropdown = Select(self.driver.find_element(By.XPATH, *locator))
        dropdown.select_by_value(value)

    def wait_for_element_present(self, locator, timeout=10):
        return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(locator))

    def set_main_window_before_switching(self):
        self.main_window = self.driver.current_window_handle

    def alert_handling(self):
        try:
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            print("ALter text:", alert.text)
            alert.accept()
            print("Alert accepted")
        except Exception as e:
            print("[ERROR] Alert not found. Alert not accepted.")
