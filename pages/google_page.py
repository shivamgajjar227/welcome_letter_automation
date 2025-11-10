from selenium.common import StaleElementReferenceException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
import time

from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pages.base_page import BasePage


class GooglePage(BasePage):
    search_box = (By.NAME, "q")
    result_block = (By.CSS_SELECTOR, "div.MjjYud")
    more_places = (By.XPATH, "//span[text()='More places' or normalize-space()='More Places']")
    place_cards = (By.XPATH, ".//span[@class='OSrXXb']")
    place_address = (By.XPATH, "//span[@class='LrzXr']")
    place_phone = (By.XPATH, "//span[starts-with(@aria-label, 'Call phone number')]")
    name = (By.XPATH, "//h2[contains(@class, 'qrShPb')]//span")

    def search_query(self, query):
        box = self.driver.find_element(*self.search_box)
        box.clear()
        box.send_keys(query)
        box.submit()
        time.sleep(3)

    def get_results(self):
        results = []
        elements = self.driver.find_elements(*self.result_block)
        for e in elements:
            try:
                title = e.find_element(By.TAG_NAME, "h3").text
                link = e.find_element(By.TAG_NAME, "a").get_attribute("href")
                desc = e.find_element(By.CSS_SELECTOR, "div.VwiC3b").text
                results.append({"title": title, "link": link, "desc": desc})
            except:
                continue
        return results

    def click_more_places(self):
        """Click 'More places' under the map results"""
        try:
            more = self.driver.find_element(*self.more_places)
            more.click()
            time.sleep(5)
        except Exception as e:
            print("⚠️ 'More places' link not found or blocked by CAPTCHA:", e)

    def click_each_place_and_get_details(self):
        wait = WebDriverWait(self.driver, 10)
        results = []
        last_count = 0

        while True:
            # Fetch fresh list of places
            places = self.driver.find_elements(*self.place_cards)
            total_places = len(places)
            print(f"🔍 Found {total_places} places (loaded)")

            if total_places == last_count:
                # No new places loaded, stop scrolling
                break
            last_count = total_places

            for i in range(len(places)):
                try:
                    # Re-fetch the element to avoid stale references
                    place = self.driver.find_elements(*self.place_cards)[i]
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", place)
                    time.sleep(5)

                    # Click the place
                    wait.until(EC.element_to_be_clickable((By.XPATH, ".//span[@class='OSrXXb']")))
                    try:
                        place.click()
                    except ElementClickInterceptedException:
                        self.driver.execute_script("arguments[0].click();", place)

                    time.sleep(5)  # wait for detail panel

                    # Extract details
                    try:
                        name = self.driver.find_element(*self.name).text
                    except NoSuchElementException:
                        name = "N/A"

                    try:
                        address = self.driver.find_element(*self.place_address).text
                    except NoSuchElementException:
                        address = "N/A"

                    try:
                        phone = self.driver.find_element(*self.place_phone).text
                    except NoSuchElementException:
                        phone = "N/A"

                    # Avoid duplicates
                    if not any(d["name"] == name for d in results):
                        results.append({
                            "name": name,
                            "address": address,
                            "phone": phone
                        })
                        print(f"✅ {name} | {address} | {phone}")

                    # Go back to list
                    self.driver.back()
                    time.sleep(2)

                except StaleElementReferenceException:
                    print(f"⚠️ Stale element at index {i}, retrying...")
                    continue
                except Exception as e:
                    print(f"❌ Failed on {i + 1}: {e}")
                    continue

            # Scroll the container to load more results
            # self.driver.execute_script("document.querySelector('.m6QErb').scrollBy(0, 500);")
            time.sleep(2)

        print(f"📋 Extracted {len(results)} places")
        return results

    def get_results(self):
        results = []
        elements = self.driver.find_elements(*self.result_block)
        for e in elements:
            try:
                title = e.find_element(By.TAG_NAME, "h3").text
                link = e.find_element(By.TAG_NAME, "a").get_attribute("href")
                desc = e.find_element(By.CSS_SELECTOR, "div.VwiC3b").text
                results.append({"title": title, "link": link, "desc": desc})
            except:
                continue
        return results

    def scroll_until_all_loaded(self):
        """Scroll down until all places are loaded"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        print("✅ All places loaded after scrolling.")