from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from core import loggin_utils
import logging
from pages.base_page import BasePage


log_name = "PRSiteLG"
logger_setup = loggin_utils.setup_logger(log_name, level='INFO')
logger = logging.getLogger(log_name)

class PRSiteLG(BasePage):

    advanced = (By.XPATH, "//button[@id='details-button']")
    proceed_lin = (By.XPATH, "//a[@id='proceed-link']")
    username_filed = (By.XPATH, "//input[@id='user_email']")
    password_filed = (By.XPATH, "//input[@id='user_password']")
    next_btn = (By.XPATH, "//button[@aria-label='Next']")
    login_btn = (By.XPATH, "//button[@aria-label='Log in']")
    welcome_letter_qc = (By.XPATH, "//div[@role='option']")

    def click_advanced(self):
        logger.info(f"Inside click Advanced-")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.advanced)
            ).click()
            logger.info("Out from click advanced")
        except Exception as e:
            print(f" Unexpected error while checking Edit button: {type(e).__name__}")

    def click_proceed_link(self):
        logger.info(f"Inside click proceed link")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.proceed_lin)
            ).click()
            logger.info("Out from click proceed link")
        except Exception as e:
            print(f" Unexpected error while checking Edit button: {type(e).__name__}")

    def is_login_page(self):
        try:
            return self.driver.find_element(By.ID, "user_email") is not None
        except:
            return False