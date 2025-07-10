from selenium import webdriver

def get_driver(browser_name="chrome"):
    if browser_name.lower() == "chrome":
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        driver = webdriver.Chrome(options=options)
    elif browser_name.lower() == "firefox":
        driver = webdriver.Firefox()
    else:
        raise Exception("Unsupported browser!")
    return driver
