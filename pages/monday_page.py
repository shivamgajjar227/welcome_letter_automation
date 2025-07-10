from selenium.webdriver.common.by import By
from pages.base_page import BasePage

class MondayPage(BasePage):

    username_filed = (By.XPATH, "//input[@id='user_email']")
    password_filed = (By.XPATH, "//input[@id='user_password']")
    login_btn = (By.XPATH, "//button[@aria-label='Log in']")

    def login(self, username, password):

        self.enter_text(self.username_filed, username)
        self.enter_text(self.password_filed, password)
        self.click(self.login_btn)
