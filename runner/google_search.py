import argparse
from typing import List, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


def fetch_google_results(query: str, limit: int = 3) -> List[Tuple[str, str]]:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    try:
        driver.get("https://www.google.com/")

        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.send_keys(query)
        search_box.send_keys(Keys.RETURN)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#search a h3"))
        )

        headings = driver.find_elements(By.CSS_SELECTOR, "div#search a h3")
        results: List[Tuple[str, str]] = []
        for heading in headings:
            if len(results) >= limit:
                break

            anchor = heading.find_element(By.XPATH, "./ancestor::a")
            title = heading.text.strip()
            link = anchor.get_attribute("href")
            if title and link:
                results.append((title, link))

        return results
    finally:
        driver.quit()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch the first Google search results for a query."
    )
    parser.add_argument("query", help="Text to search for")
    parser.add_argument(
        "--limit", type=int, default=3, help="Number of results to return (default: 3)"
    )
    args = parser.parse_args()

    results = fetch_google_results(args.query, args.limit)
    for index, (title, link) in enumerate(results, start=1):
        print(f"{index}. {title}\n   {link}")


if __name__ == "__main__":
    main()
