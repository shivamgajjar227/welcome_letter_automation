import logging
import time
import allure
from selenium.webdriver.common.by import By

from drivers.allure_decorator import allure_log_step
from pages.base_page import BasePage
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from core import loggin_utils

log_name = "MondayPage"
logger_setup = loggin_utils.setup_logger(log_name, level='INFO')
logger = logging.getLogger(log_name)

class MondayPage(BasePage):

    username_filed = (By.XPATH, "//input[@id='user_email']")
    password_filed = (By.XPATH, "//input[@id='user_password']")
    login_btn = (By.XPATH, "//button[@aria-label='Log in']")
    welcome_letter_qc = (By.XPATH, "//div[@role='option']")
    search_button = (By.XPATH, "//div[@class='board-filter-input-container boardFilterInputContainer--6Cols board-filter-search board-filter-input-container--expandable']")
    enter_npi_search = (By.XPATH, "//div[@class='board-filter-input-container boardFilterInputContainer--6Cols board-filter-search board-filter-input-container--expandable']")
    not_started = (By.XPATH, "//div[contains(text(),'Not Started')]")
    done_button = (By.XPATH, "//li[@id='1']//div[@class='status-color-background']//div//div[@class='ds-text-component']")
    cross = (By.XPATH, "//button[@aria-label='Clear search']//*[name()='svg']")

    @allure_log_step("Login to Monday.com")
    @allure.story("Do login with username: {1} and password: ****")
    def login(self, username, password):
        logger.info("Inside login method of MondayPage")
        self.enter_text(self.username_filed, username)
        self.enter_text(self.password_filed, password)
        self.click(self.login_btn)
        logger.info("Out from Monday logging func")

    @allure_log_step("Clicking Welcome Letter QC")
    def click_welcome_letter_qc(self):
        logger.info(f"Inside click Welcome letter QC")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.welcome_letter_qc)
            ).click()
            logger.info("Out from click welcome letter qc")
        except Exception as e:
            print(f" Unexpected error while checking Edit button: {type(e).__name__}")

    @allure_log_step("Clicking Search button and Get NPI Data")
    def get_pr_site_npis(self):
        time.sleep(2)
        logger.info("Inside get PR Site Npis")
        group = self.driver.find_element(By.XPATH, "//div[contains(@data-testid, 'heading')]//text2[text()='PR Site']")
        group_container = self.driver.find_element(By.XPATH, "//div[@id='board-wrapper-first-level-content']")

        npis = []
        last_height = 0
        same_height_count = 0  # to detect when we've reached the bottom

        while True:
            rows = group_container.find_elements(By.XPATH, ".//div[contains(@data-testid, 'item-')]")

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
                        lob_list = []
                        try:
                            # Try finding the usual chips list container (for multiple LoBs)
                            lob_containers = row.find_elements(By.XPATH,
                                                               ".//div[contains(@class, 'chips-list-module_chips__CTQcD')]")

                            if lob_containers:
                                # Case 1: Multiple LoBs
                                lob_chips = lob_containers[0].find_elements(By.XPATH, ".//div[@data-testid='chip']")
                                for chip in lob_chips:
                                    lob_text = chip.find_element(By.XPATH, ".//div[@data-testid='text']").text.strip()
                                    if lob_text:
                                        lob_list.append(lob_text)
                            else:
                                # Case 2: Single LoB (like 'Medicare')
                                single_lob = row.find_element(By.XPATH,
                                                              ".//div[@data-testid='chip']//div[@data-testid='text']").text.strip()
                                lob_list.append(single_lob)

                        except Exception as lob_error:
                                print(f"Error extracting LoB: {lob_error}")

                        lines_of_business = ", ".join(lob_list)
                        entry = {
                            "npi_number": npi_number.strip(),
                            "effective_date": effective_date.strip(),
                            "health_plan": health_plan.strip(),
                            "lines_of_business": lines_of_business.strip()
                        }
                        if entry not in npis:
                            npis.append(entry)
                except Exception as e:
                    print(f"Error in Monday.com while fetching data: {e}")

            self.driver.execute_script("arguments[0].scrollBy(0, 500);", group_container)
            time.sleep(1.5)

            new_height = self.driver.execute_script("return arguments[0].scrollTop", group_container)
            if new_height == last_height:
                same_height_count += 1
            else:
                same_height_count = 0
            last_height = new_height

            if same_height_count > 2:
                break
            logger.info("Out from get PR Site Npis")

        return npis

    def get_not_started_npis(self):
        # Locate the "PR Site" section
        group = self.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@data-testid, 'heading')]//text2[text()='FCC - November 2025 - Cardiology']")
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

    def click_search_button(self):
        WebDriverWait(self.driver, 8).until(
            EC.element_to_be_clickable(self.search_button)
        ).click()

    def enter_npi_button(self, value):
        logger.info(f"Inside Enter NPI Button:{value}")
        try:
            # Wait for the "Search this board" input
            search_input = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//input[@placeholder='Search this board']"))
            )
            search_input.clear()
            search_input.send_keys(str(value))
            logger.info(f"Out from Enter NPI Button:{value}")

        except Exception as e:
            print(f"Error while entering npi button: {e}")

    def click_not_started(self):
        logger.info(f"Inside Click Not Started")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.not_started)
            ).click()
            logger.info(f"Out from Click Not Started")
        except Exception as e:
            print(f"Error while click not started: {e}")

    def click_done_button(self):
        logger.info(f"Inside Click Done Button")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.done_button)
            ).click()
            logger.info(f"Out from Click Done Button")
        except Exception as e:
            print(f"Error while click done button: {e}")

    def click_cross_button(self):
        logger.info(f"Inside Click Cross Button")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.cross)
            ).click()
            logger.info(f"Out from Click Cross Button")
        except Exception as e:
            print(f"Error while click cross button: {e}")

    @allure_log_step("Checks Login Page is Open or not")
    def is_login_page(self):
        try:
            return self.driver.find_element(By.ID, "user_email") is not None
        except:
            return False


    def get_fcc_npis(self):
        time.sleep(2)
        logger.info("Inside get PR Site Npis")
        group = self.driver.find_element(By.XPATH, "//div[contains(@data-testid, 'heading')]//text2[text()='FCC - November 2025 - Cardiology']")
        group_container = self.driver.find_element(By.XPATH, "//div[@id='board-wrapper-first-level-content']")

        npis = []
        last_height = 0
        same_height_count = 0  # to detect when we've reached the bottom

        while True:
            rows = group_container.find_elements(By.XPATH, ".//div[contains(@data-testid, 'item-')]")

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
                        lob_list = []
                        try:
                            # Try finding the usual chips list container (for multiple LoBs)
                            lob_containers = row.find_elements(By.XPATH,
                                                               ".//div[contains(@class, 'chips-list-module_chips__CTQcD')]")

                            if lob_containers:
                                # Case 1: Multiple LoBs
                                lob_chips = lob_containers[0].find_elements(By.XPATH, ".//div[@data-testid='chip']")
                                for chip in lob_chips:
                                    lob_text = chip.find_element(By.XPATH, ".//div[@data-testid='text']").text.strip()
                                    if lob_text:
                                        lob_list.append(lob_text)
                            else:
                                # Case 2: Single LoB (like 'Medicare')
                                single_lob = row.find_element(By.XPATH,
                                                              ".//div[@data-testid='chip']//div[@data-testid='text']").text.strip()
                                lob_list.append(single_lob)

                        except Exception as lob_error:
                            print(f"Error extracting LoB: {lob_error}")

                        lines_of_business = ", ".join(lob_list)
                        entry = {
                            "npi_number": npi_number.strip(),
                            "effective_date": effective_date.strip(),
                            "health_plan": health_plan.strip(),
                            "lines_of_business": lines_of_business.strip()
                        }
                        if entry not in npis:
                            npis.append(entry)
                except Exception as e:
                    print(f"Error in Monday.com while fetching data: {e}")

            self.driver.execute_script("arguments[0].scrollBy(0, 500);", group_container)
            time.sleep(1.5)

            new_height = self.driver.execute_script("return arguments[0].scrollTop", group_container)
            if new_height == last_height:
                same_height_count += 1
            else:
                same_height_count = 0
            last_height = new_height

            if same_height_count > 2:
                break
            logger.info("Out from get PR Site Npis")

        return npis