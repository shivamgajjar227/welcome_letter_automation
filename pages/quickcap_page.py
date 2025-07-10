from selenium.webdriver.common.by import By
from pages.base_page import BasePage

class QuickcapPage(BasePage):

    USERNAME_FIELD = (By.XPATH, "//input[@id='TaRtxt_username']")
    PASSWORD_FIELD = (By.XPATH, "//input[@id='TaRpas_password']")
    LOGIN_BUTTON = (By.XPATH, "//input[@value='LOGIN']")
    select_company = (By.XPATH, "//td[@class='clientBold']//a[@id='comptda_DNSHUMANA']")

    def login(self, username, password):
        self.enter_text(self.USERNAME_FIELD, username)
        self.enter_text(self.PASSWORD_FIELD, password)
        self.click(self.LOGIN_BUTTON)

    def choose_company(self):
        self.click(self.select_company)



