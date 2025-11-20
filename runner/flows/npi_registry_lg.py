from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


class MondayLogin:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)

    def login(self, email, password):
        try:
            # Navigate to Monday.com
            self.driver.get("https://monday.com")

            # Click login button
            login_btn = self.wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log in')]")))
            login_btn.click()

            # Enter email
            email_field = self.wait.until(EC.presence_of_element_located((By.NAME, "email")))
            email_field.clear()
            email_field.send_keys(email)

            # Click continue
            continue_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')]")))
            continue_btn.click()

            # Enter password
            password_field = self.wait.until(EC.presence_of_element_located((By.NAME, "password")))
            password_field.clear()
            password_field.send_keys(password)

            # Click login
            final_login_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Log in')]")))
            final_login_btn.click()

            # Wait for dashboard to load
            self.wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'board')]")))
            print("Monday.com login successful")
            return True

        except Exception as e:
            print(f"Monday.com login failed: {str(e)}")
            return False