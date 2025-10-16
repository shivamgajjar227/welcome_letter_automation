"""
Browser factory utilities for headless Selenium sessions.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Iterator, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions

try:
    import chromedriver_autoinstaller  # type: ignore
except Exception:  # pragma: no cover - optional dep
    chromedriver_autoinstaller = None  # type: ignore

from .context import RunnerMetadata

logger = logging.getLogger(__name__)


DEFAULT_WINDOW_SIZE = "1920,1080"


def build_chrome_options(headless: bool = True) -> ChromeOptions:
    """Construct ChromeOptions with sane defaults for headless execution."""
    options = ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument(f"--window-size={DEFAULT_WINDOW_SIZE}")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--allow-insecure-localhost")
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    return options


def _ensure_local_driver() -> None:
    """Install chromedriver that matches the local Chrome binary."""
    if chromedriver_autoinstaller is None:
        logger.warning("chromedriver-autoinstaller not available; assuming driver on PATH")
        return
    path = chromedriver_autoinstaller.install()
    logger.info("Chromedriver ensured at %s", path)


def create_driver(metadata: RunnerMetadata, headless: bool = True) -> webdriver.Chrome:
    """
    Create a Chrome WebDriver instance based on metadata.

    Preference order:
      1. Remote WebDriver if `selenium_url` is provided.
      2. Local ChromeDriver (auto-installed if possible).
    """
    options = build_chrome_options(headless=headless)
    selenium_url: Optional[str] = metadata.selenium_url or None

    if selenium_url:
        logger.info("Connecting to remote Selenium hub at %s", selenium_url)
        driver = webdriver.Remote(command_executor=selenium_url, options=options)
        return driver  # type: ignore[return-value]

    _ensure_local_driver()
    logger.info("Launching local ChromeDriver session")
    return webdriver.Chrome(options=options)


@contextlib.contextmanager
def browser_session(metadata: RunnerMetadata, headless: bool = True) -> Iterator[webdriver.Chrome]:
    """Context manager that yields a configured WebDriver and guarantees teardown."""
    driver = create_driver(metadata, headless=headless)
    try:
        yield driver
    finally:
        try:
            driver.quit()
        except Exception:  # pragma: no cover - best-effort cleanup
            logger.exception("Error while quitting WebDriver")

