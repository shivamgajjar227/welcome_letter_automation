from selenium.webdriver.common.by import By
from pages.base_page import BasePage
from selenium.webdriver.support import expected_conditions as EC

class MondayPage(BasePage):

    username_filed = (By.XPATH, "//input[@id='user_email']")
    password_filed = (By.XPATH, "//input[@id='user_password']")
    login_btn = (By.XPATH, "//button[@aria-label='Log in']")
    welcome_letter_qc = (By.XPATH, "//div[@role='option']")

    def login(self, username, password):

        self.enter_text(self.username_filed, username)
        self.enter_text(self.password_filed, password)
        self.click(self.login_btn)

    def click_welcome_letter_qc(self):
        self.click(self.welcome_letter_qc)

    def get_not_started_npis(self):
        # Locate the "PR Site" section
        group_container = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//text2[text()='PR Site']/ancestor::div[contains(@class,'group-header-component-title-row')]/following-sibling::div")
            )
        )

        # Get all row wrappers under this group
        rows = group_container.find_elements(By.XPATH, ".//div[contains(@data-testid,'row-wrapper')]")

        npis = []

        for row in rows:
            try:
                # Adjust column indexes based on screenshot — these are examples
                status = row.find_element(By.XPATH, ".//div[contains(@class,'status-cell-inner')]").text.strip()
                if status.lower() == "not started":
                    # This assumes NPI is at column position 6 or 7 in the grid — adjust if needed
                    npi = row.find_elements(By.XPATH, ".//div[@data-testid='cell']")[6].text.strip()
                    npis.append(npi)
            except Exception as e:
                print(f"Skipped a row due to: {e}")
                continue

        return npis
