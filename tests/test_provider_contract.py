from selenium import webdriver
from pages.monday_lg_page import MondayLGPage
from pages.pr_site_lg_page import PRSiteLG


def test_monday_login():
    driver = webdriver.Chrome()
    driver.get("https://auth.monday.com/")

    try:
        monday = MondayLGPage(driver)
        monday.login("autoprocess@pns-mgmt.com", "@VEnger200@@@@")
        print("Login test passed")
        monday.click_welcome_letter_qc()

    except Exception as e:
        print("Login failed:", e)
        raise e

    finally:
        driver.quit()


def test_pr_site_login():
    driver = webdriver.Chrome()
    driver.get("https://pss.ad.pns-mgmt.com/ProvPractice.aspx#s1")

    try:
        prsite = PRSiteLG(driver)
        prsite.click_advanced()
        prsite.click_proceed_link()
        # prsite.login("autoprocess@ad.pns-mgmt.com", "P%23194714496192ab")
        # print("Login test passed")
        # monday.click_welcome_letter_qc()

    except Exception as e:
        print("Login failed:", e)
        raise e

    finally:
        driver.quit()