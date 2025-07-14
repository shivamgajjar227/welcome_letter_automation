from selenium.webdriver.support.wait import WebDriverWait

class BasePage:
    def __init__(self, driver):
        self.new_window = None
        self.main_window = None
        self.driver = driver

    def click(self, locator):
        self.driver.find_element(*locator).click()

    def enter_text(self, locator, text):
        self.driver.find_element(*locator).clear()
        self.driver.find_element(*locator).send_keys(text)

    def switch_to_new_window(self):
        self.main_window = self.driver.current_window_handle
        WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > 1)
        new_window = [h for h in self.driver.window_handles if h != self.main_window][0]
        self.driver.switch_to.window(new_window)
        self.new_window = new_window

    def switch_back_to_main(self):
        self.driver.switch_to.window(self.main_window)