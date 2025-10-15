from selenium import webdriver
from selenium.webdriver.chrome.options import Options

#
# def get_driver(browser_name="chrome"):
#     if browser_name.lower() == "chrome":
#         options = webdriver.ChromeOptions()
#         options.add_argument("--start-maximized")
#         options.add_argument("--ignore-certificate-errors")
#         options.add_argument("--ignore-ssl-errors")
#         options.add_argument("--allow-insecure-localhost")
#         # options.add_argument("--headless")
#         # options.add_argument("--no-sandbox")
#
#         driver = webdriver.Chrome(options=options)
#     elif browser_name.lower() == "firefox":
#         driver = webdriver.Firefox()
#     else:
#         raise Exception("Unsupported browser!")
#     return driver

def get_driver(browser_name="chrome", headless=True):
    if browser_name.lower() == "chrome":
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        options.add_argument("--allow-insecure-localhost")

        if headless:
            options.add_argument("--headless")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")

        driver = webdriver.Chrome(options=options)
    elif browser_name.lower() == "firefox":
        driver = webdriver.Firefox()
    else:
        raise Exception("Unsupported browser!")
    return driver

