from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from core import loggin_utils
import logging
from pages.base_page import BasePage


log_name = "MondayLGPage"
logger_setup = loggin_utils.setup_logger(log_name, level='INFO')
logger = logging.getLogger(log_name)

class MondayLGPage(BasePage):
    username_filed = (By.XPATH, "//input[@id='user_email']")
    password_filed = (By.XPATH, "//input[@id='user_password']")
    login_btn = (By.XPATH, "//button[@aria-label='Log in']")
    welcome_letter_qc = (By.XPATH, "//div[@role='option']")


    def login(self, username, password):
        logger.info("Inside login method of MondayPage")
        self.enter_text(self.username_filed, username)
        self.enter_text(self.password_filed, password)
        self.click(self.login_btn)
        logger.info("Out from Monday logging func")

    def click_welcome_letter_qc(self):
        logger.info(f"Inside click Welcome letter QC")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.welcome_letter_qc)
            ).click()
            logger.info("Out from click welcome letter qc")
        except Exception as e:
            print(f" Unexpected error while checking Edit button: {type(e).__name__}")

    def is_login_page(self):
        try:
            return self.driver.find_element(By.ID, "user_email") is not None
        except:
            return False