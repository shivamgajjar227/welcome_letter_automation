import logging
import time
import allure
from selenium.webdriver.common.by import By
from pages.base_page import BasePage
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from core import loggin_utils
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains



log_name = "MondayPage"
logger_setup = loggin_utils.setup_logger(log_name, level='INFO')
logger = logging.getLogger(log_name)

class MondayStatusPage(BasePage):
    username_filed = (By.XPATH, "//input[@id='user_email']")
    password_filed = (By.XPATH, "//input[@id='user_password']")
    login_btn = (By.XPATH, "//button[@aria-label='Log in']")
    welcome_letter_qc = (By.XPATH, "//div[@role='option']")
    search_button = (By.XPATH,
                     "//div[@class='board-filter-input-container boardFilterInputContainer--6Cols board-filter-search board-filter-input-container--expandable']")
    enter_npi_search = (By.XPATH,
                        "//div[@class='board-filter-input-container boardFilterInputContainer--6Cols board-filter-search board-filter-input-container--expandable']")
    not_started = (By.XPATH, "//div[contains(text(),'Not Started')]")
    done_button = (By.XPATH,
                   "//span[normalize-space()='Review']")
    cross = (By.XPATH, "//button[@aria-label='Clear search']//*[name()='svg']")
    roadblock_button = (By.XPATH, "//span[normalize-space()='Roadblock']")
    remarks = (By.XPATH, "(//div[@role='presentation'])[52]")
    enter_remarks = (By.XPATH, "//div[contains(@class,'text-cell-view-module_wrapperComponent__VMKAw')]")

    @allure.story("Do login with username: {1} and password: ****")
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
                        lines_of_business = row.find_element(By.XPATH,
                                                             ".//div[contains(@class, 'col-identifier-dropdown_mkt4m1wd')]//div[@data-testid='text']").text

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
                (By.XPATH, "//div[contains(@data-testid, 'heading')]//text2[text()='PR Site']")
            )
        )

        # 2. Get the parent container of all rows for that group (adjust the XPATH to your DOM structure)
        group_container = group.find_element(By.XPATH,
                                             "./ancestor::div[contains(@class, 'group-header-wrapper')]/following-sibling::div")

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

    def click_review_button(self):
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

    def is_login_page(self):
        try:
            return self.driver.find_element(By.ID, "user_email") is not None
        except:
            return False

    def click_roadblock_button(self):
        logger.info(f"Inside Click Roadblock Button")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.roadblock_button)
            ).click()
            logger.info(f"Out from Click Roadblock Button")
        except Exception as e:
            print(f"Error while click Roadblock button: {e}")

    # def enter_remarks(self, remarks_text: str):
    #     logger.info("Inside Enter Remarks")
    #
    #     # Click the remarks cell
    #     remarks_cell = WebDriverWait(self.driver, 10).until(
    #         EC.element_to_be_clickable((By.XPATH,
    #                                     "(//div[@role='presentation'])[52]"))
    #     )
    #     remarks_cell.click()
    #
    #     # Wait for the editable input/textarea
    #     input_box = WebDriverWait(self.driver, 10).until(
    #         EC.presence_of_element_located((By.XPATH, "//input[@type='text' or @role='textbox']"))
    #     )
    #
    #     # Clear and enter remarks
    #     input_box.clear()
    #     input_box.send_keys(remarks_text)
    #     input_box.send_keys(Keys.ENTER)
    #
    #     logger.info(f"Entered remarks: {remarks_text}")

    def enter_remarks1(self, value):
        logger.info(f"Inside Enter Remarks: {value}")
        try:
            remarks_cell = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH,
                                            "(//div[contains(@class,'text-cell-view-module_wrapperComponent__VMKAw')])[4]"))
            )
            remarks_cell.click()

            # Step 2: Wait for input field to appear inside the cell
            input_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                                                "(//div[contains(@class,'text-cell-view-module_wrapperComponent__VMKAw')])[4]//input | "
                                                "(//div[contains(@class,'text-cell-view-module_wrapperComponent__VMKAw')])[4]//textarea"
                                                ))
            )

            # Step 3: Clear and type
            input_field.clear()
            input_field.send_keys(value)

            print(f"Remarks '{value}' entered successfully.")
            logger.info(f"Out from Enter Remarks: {value}")

        except Exception as e:
            print(f"Error in entering Remarks: {e}")

    def get_all_health_plans_from_ui(self):
        """
        Return ALL health plans including duplicates
        """
        health_plans = []
        try:
            time.sleep(3)

            all_chips = self.driver.find_elements(By.XPATH, "//div[contains(@class, 'chips-list-module_chip__gp-E8')]")
            non_healthplans = ['Medicare', 'Medicaid', 'Commercial']

            for chip in all_chips:
                text = chip.text.strip()
                if text and text not in non_healthplans:
                    health_plans.append(text)  # Allow duplicates
                    print(f"✅ Health plan: {text}")

            print(f"🎯 All health plans (with duplicates): {health_plans}")
            return health_plans

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def process_rows_and_enter_remarks(self, db_health_plan, db_effective_date, remarks_text):
        """
        Process all rows, check health plan and effective date, and enter remarks in matching rows
        """
        try:
            time.sleep(3)

            # Get all rows
            rows = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'pulse-component-wrapper')]"))
            )
            print(f"📊 Found {len(rows)} rows to check")

            matching_rows_count = 0

            for row_index, row in enumerate(rows):
                print(f"🔍 Checking row {row_index + 1}...")

                # Get health plan from this row
                row_health_plan = None
                try:
                    health_plan_elements = row.find_elements(By.XPATH,
                                                             ".//div[contains(@class, 'chips-list-module_chip__gp-E8')]")
                    for element in health_plan_elements:
                        text = element.text.strip()
                        if text and text not in ['Medicare', 'Medicaid', 'Commercial']:
                            row_health_plan = text
                            break
                except Exception as e:
                    print(f"Error getting health plan from row: {e}")

                # Get effective date from this row
                row_effective_date = None
                try:
                    date_selectors = [
                        ".//div[contains(@class, 'date-cell-component')]//div[contains(@class, 'ds-text-component')]",
                        ".//div[contains(@class, 'grid-cell-component-wrapper')][6]//div[contains(@class, 'ds-text-component')]",
                        ".//div[contains(@class, 'date-cell')]//span"
                    ]
                    for selector in date_selectors:
                        try:
                            date_elements = row.find_elements(By.XPATH, selector)
                            for element in date_elements:
                                text = element.text.strip()
                                if text and any(month in text.lower() for month in
                                                ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct',
                                                 'nov', 'dec']):
                                    row_effective_date = text
                                    break
                            if row_effective_date:
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"Error getting effective date from row: {e}")

                # Compare health plans
                health_plan_match = False
                if row_health_plan and db_health_plan:
                    db_hp_clean = db_health_plan.strip().lower()
                    ui_hp_clean = row_health_plan.strip().lower()
                    health_plan_match = db_hp_clean in ui_hp_clean or ui_hp_clean in db_hp_clean

                # Compare dates
                effective_date_match = False
                if row_effective_date and db_effective_date:
                    db_date_clean = db_effective_date.strip().lower()
                    ui_date_clean = row_effective_date.strip().lower()
                    month_abbreviations = {
                        'jan': 'january', 'feb': 'february', 'mar': 'march', 'apr': 'april',
                        'may': 'may', 'jun': 'june', 'jul': 'july', 'aug': 'august',
                        'sep': 'september', 'oct': 'october', 'nov': 'november', 'dec': 'december'
                    }
                    effective_date_match = (db_date_clean in ui_date_clean or
                                            ui_date_clean in db_date_clean or
                                            any(db_date_clean.startswith(month) and ui_date_clean.startswith(month)
                                                for month in month_abbreviations.keys()))

                # Check if BOTH health plan AND effective date match
                if health_plan_match and effective_date_match:
                    print(
                        f"✅ FULL MATCH found in row {row_index + 1}: Health Plan: {row_health_plan}, Date: {row_effective_date}")

                    # Add remarks to this specific row
                    try:
                        remarks_cell = row.find_element(By.XPATH,
                                                        ".//div[contains(@class,'text-cell-view-module_wrapperComponent__VMKAw')]")

                        (ActionChains(self.driver)
                         .click(remarks_cell)
                         .pause(2)
                         .send_keys(remarks_text)
                         .pause(0.5)
                         .send_keys(Keys.RETURN)
                         .perform())

                        time.sleep(1)
                        matching_rows_count += 1
                        print(f"✅ Remarks added to row {row_index + 1}")

                    except Exception as e:
                        print(f" Failed to add remarks to row {row_index + 1}: {e}")
                else:
                    print(f" No match in row {row_index + 1}")
                    print(f"   Row HP: {row_health_plan}, Row Date: {row_effective_date}")
                    print(f"   DB HP: {db_health_plan}, DB Date: {db_effective_date}")
                    print(f"   HP Match: {health_plan_match}, Date Match: {effective_date_match}")

            print(f"🎯 Total {matching_rows_count} rows updated with remarks")
            return matching_rows_count > 0

        except Exception as e:
            print(f"❌ Error in process_rows_and_enter_remarks: {e}")
            return False

    def click_not_started_for_matching_health_plans(self, db_health_plan):
        """
        Process all rows, check health plan, and click Not Started on matching rows
        """
        try:
            time.sleep(3)

            # Get all rows
            rows = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//div[contains(@class, 'pulse-component-wrapper')]"))
            )
            print(f"📊 Found {len(rows)} rows to check")

            matching_rows_count = 0

            for row_index, row in enumerate(rows):
                print(f"🔍 Checking row {row_index + 1}...")

                # Get health plan from this row
                row_health_plan = None
                try:
                    health_plan_elements = row.find_elements(By.XPATH,
                                                             ".//div[contains(@class, 'chips-list-module_chip__gp-E8')]")
                    for element in health_plan_elements:
                        text = element.text.strip()
                        if text and text not in ['Medicare', 'Medicaid', 'Commercial']:
                            row_health_plan = text
                            break
                except Exception as e:
                    print(f"Error getting health plan from row: {e}")

                # Compare health plans
                health_plan_match = False
                if row_health_plan and db_health_plan:
                    db_hp_clean = db_health_plan.strip().lower()
                    ui_hp_clean = row_health_plan.strip().lower()
                    health_plan_match = db_hp_clean in ui_hp_clean or ui_hp_clean in db_hp_clean

                # Check if health plan matches
                if health_plan_match:
                    print(f"✅ Health plan match found in row {row_index + 1}: {row_health_plan}")

                    try:
                        # Click Not Started for this row
                        not_started_btn = row.find_element(By.XPATH,
                                                           ".//div[contains(@class, 'status-cell-component')]")
                        not_started_btn.click()
                        time.sleep(1)
                        print(f"✅ Not Started clicked on row {row_index + 1}")

                        matching_rows_count += 1

                    except Exception as e:
                        print(f"❌ Failed to click Not Started on row {row_index + 1}: {e}")
                else:
                    print(f"❌ No health plan match in row {row_index + 1}")
                    print(f"   Row HP: {row_health_plan}, DB HP: {db_health_plan}")

            print(f"🎯 Total {matching_rows_count} rows with Not Started clicked")
            return matching_rows_count > 0

        except Exception as e:
            print(f"❌ Error in click_not_started_for_matching_health_plans: {e}")
            return False
