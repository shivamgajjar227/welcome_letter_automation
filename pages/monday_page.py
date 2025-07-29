import time

from selenium.webdriver.common.by import By
from pages.base_page import BasePage
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

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
        WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable(self.welcome_letter_qc)
        ).click()

    def get_pr_site_npis(self):

        # 1. Find the group with title 'PR Site'
        time.sleep(2)
        group = self.driver.find_element(By.XPATH, "//div[contains(@data-testid, 'heading')]//text2[text()='PR Site']")

        # 2. Get the parent container of all rows for that group (adjust the XPATH to your DOM structure)
        group_container = group.find_element(By.XPATH,
                                             "./ancestor::div[contains(@role, 'grid')]")

        # 3. Find all rows in this group
        rows = group_container.find_elements(By.XPATH, ".//div[contains(@data-testid, 'item-')]")

        npis = []
        for row in rows:
            try:
                status = row.find_element(By.XPATH,
                                          ".//div[contains(@class, 'col-identifier-status')]//div[@data-testid='text']").text
                if status.strip() == "Not Started":
                    npi_number = row.find_element(By.XPATH,
                                                    ".//div[contains(@class, 'col-identifier-text_mkt42ppc')]//div[@data-testid='text']").text
                    effective_date = row.find_element(By.XPATH,
                                                      ".//div[contains(@class, 'col-identifier-date4')]//span[contains(@class,'ds-text-component-content-text')]").text
                    health_plan = row.find_element(By.XPATH,
                                                   ".//div[contains(@class, 'col-identifier-dropdown_mkt4m1wd')]//div[@data-testid='text']").text
                    lines_of_business = row.find_element(By.XPATH,
                                                         ".//div[contains(@class, 'col-identifier-dropdown_mkt4r6zg')]//div[@class='chips-list-module_chips__CTQcD']").text

                    npis.append({
                        "npi_number": npi_number.strip(),
                        "effective_date": effective_date.strip(),
                        "health_plan": health_plan.strip(),
                        "lines_of_business": lines_of_business.strip()
                    })
            except Exception as e:
                print(f"Error in Monday.com while fetching data: {e}")
                continue

        return npis

    def get_not_started_npis(self):
        # Locate the "PR Site" section
        group = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@data-testid, 'heading')]//text2[text()='PR Site']")
            )
        )

        # 2. Get the parent container of all rows for that group (adjust the XPATH to your DOM structure)
        group_container = group.find_element(By.XPATH, "./ancestor::div[contains(@class, 'group-header-wrapper')]/following-sibling::div")

        # Get all row wrappers under this group
        rows = group_container.find_elements(By.XPATH, "")

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
