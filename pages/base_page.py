import time

from selenium.common import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import allure
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class BasePage:

    def __init__(self, driver):
        self.new_window = None
        self.main_window = None
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 20)

    @allure.step("Report error: {msg}, {exception}")
    def _report_error(self, msg, exception):
        allure.attach(str(exception), name="Exception", attachment_type=allure.attachment_type.TEXT)
        allure.attach(
            self.driver.get_screenshot_as_png(),
            name=msg,
            attachment_type=allure.attachment_type.PNG)

    @allure.step("Validate condition: {msg}")
    def validate(self, condition, msg):
        """Validation without assertion"""
        try:
            if not condition:
                raise Exception(msg)
        except Exception as e:
            self._report_error("Validation Failed", e)

    @allure.step("Validate condition: {msg}")
    def click(self, locator):
        try:
            element = self.wait.until(EC.element_to_be_clickable(locator))
            element.click()
        except (NoSuchElementException, TimeoutException, Exception) as e:
            self._report_error("Click Failed", e)

    @allure.step("Click button: {msg}")
    def enter_text(self, locator, text):
        try:
            self.driver.find_element(*locator).clear()
            self.driver.find_element(*locator).send_keys(text)
        except (NoSuchElementException, TimeoutException, Exception) as e:
            self._report_error("Enter Text Failed", e)

    @allure.step("Click Enter: {msg}")
    def switch_to_new_window1(self):
        try:
            time.sleep(1)
            handles = self.driver.window_handles
            if len(handles) > 1:
                self.driver.switch_to.window(handles[-1])
            else:
                self.driver.switch_to.window(handles[0])
        except (NoSuchElementException, TimeoutException, Exception) as e:
            self._report_error("Switch to New Window Failed", e)

    @allure.step("Click Button: {msg}")
    def store_main_window(self):
        try:
            """Call this once after driver opens the initial main page."""
            self.main_window = self.driver.current_window_handle
        except (NoSuchElementException, TimeoutException, Exception) as e:
            self._report_error("Store Main Window Failed", e)

    @allure.step("Navigate to main page")
    def switch_to_new_window(self):
        try:
            """Switch to the first window that is not the main window."""
            handles = self.driver.window_handles
            for h in handles:
                if h != self.main_window:
                    self.driver.switch_to.window(h)
                    return
            print("[WARN] No popup window found to switch to.")
        except (NoSuchElementException, TimeoutException, Exception) as e:
            self._report_error("Switch to New Window Failed", e)

    @allure.step("Switch to main window")
    def switch_to_main(self):
        try:
            """Switch back to the main window."""
            if self.main_window and self.main_window in self.driver.window_handles:
                self.driver.switch_to.window(self.main_window)
            else:
                print("[ERROR] Main window handle not found in current handles.")
        except (NoSuchElementException, TimeoutException, Exception) as e:
            self._report_error("Switch to Main Window Failed", e)

    @allure.step("Switch back to main window")
    def switch_back_to_main(self):
        try:
            if not self.main_window:
                raise Exception("Main window handle is not set. Did you call switch_to_new_window first?")
            self.driver.switch_to.window(self.main_window)
        except (NoSuchElementException, TimeoutException, Exception) as e:
            self._report_error("Switch Back to Main Window Failed", e)

    @allure.step("Select value '{value}' from dropdown")
    def select_value_from_dropdown(self, locator,value):
        try:
            dropdown = Select(self.driver.find_element(By.XPATH, *locator))
            dropdown.select_by_value(value)
        except (NoSuchElementException, TimeoutException, Exception) as e:
            self._report_error("Select from Dropdown Failed", e)

    @allure.step("Wait for element present: {locator}")
    def wait_for_element_present(self, locator, timeout=10):
        try:
            return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located(locator))
        except (NoSuchElementException, TimeoutException, Exception) as e:
            self._report_error("Wait for Element Present Failed", e)
            return None

    @allure.step("Set main window before switching")
    def set_main_window_before_switching(self):
        try:
            self.main_window = self.driver.current_window_handle
        except (NoSuchElementException, TimeoutException, Exception) as e:
            self._report_error("Set Main Window Failed", e)

    @allure.step("Set main window after switching")
    def alert_handling(self):
        try:
            WebDriverWait(self.driver, 10).until(EC.alert_is_present())
            alert = self.driver.switch_to.alert
            print("ALter text:", alert.text)
            alert.accept()
            print("Alert accepted")
        except (NoSuchElementException, TimeoutException, Exception) as e:
            self._report_error("Set Main Window Failed", e)
            print("[ERROR] Alert not found. Alert not accepted.")
