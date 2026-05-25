"""
Naukri Profile Auto-Updater — GitHub Actions Edition
- Runs on Linux (GitHub Actions Ubuntu runner)
- Updates First Name field to refresh "Last Updated" timestamp
- Toggles trailing space each run (state stored in toggle_state.txt,
  committed back to repo by the workflow)
- Credentials read from GitHub Secrets via environment variables
"""

import os
import time
import random
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler()]   # GitHub Actions captures stdout/stderr
)
log = logging.getLogger(__name__)

# ── Credentials from GitHub Secrets (injected as env vars by workflow) ─────────
NAUKRI_EMAIL    = os.environ.get("NAUKRI_EMAIL", "")
NAUKRI_PASSWORD = os.environ.get("NAUKRI_PASSWORD", "")

# ── Toggle state file (committed back to repo to persist across runs) ──────────
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toggle_state.txt")


def human_delay(min_s=1.0, max_s=2.5):
    time.sleep(random.uniform(min_s, max_s))


def read_toggle_state() -> bool:
    """True = add trailing space this run, False = strip it."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read().strip() == "1"
    return True


def write_toggle_state(state: bool):
    with open(STATE_FILE, "w") as f:
        f.write("1" if state else "0")


def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def login(driver):
    log.info("Navigating to Naukri login …")
    driver.get("https://www.naukri.com/nlogin/login")
    human_delay(3, 5)

    email_el = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "usernameField"))
    )
    email_el.clear()
    email_el.send_keys(NAUKRI_EMAIL)
    human_delay()

    pwd_el = driver.find_element(By.ID, "passwordField")
    pwd_el.clear()
    pwd_el.send_keys(NAUKRI_PASSWORD)
    human_delay()

    pwd_el.send_keys(Keys.RETURN)
    human_delay(5, 7)

    if "nlogin" in driver.current_url:
        # Save screenshot for debugging
        driver.save_screenshot("login_failed.png")
        raise RuntimeError("Login failed — check NAUKRI_EMAIL / NAUKRI_PASSWORD secrets.")

    log.info("Login successful ✓")


def update_name_field(driver):
    log.info("Opening profile page …")
    driver.get("https://www.naukri.com/mnjuser/profile")
    human_delay(4, 6)

    # Click edit on Personal Details section
    try:
        edit_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//div[contains(@class,'personalDetails') or contains(@class,'personal-details')]"
                "//span[contains(@class,'edit') or @title='Edit']"
            ))
        )
    except TimeoutException:
        edit_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//section[contains(@id,'personal')]//span[contains(@class,'edit')]"
            ))
        )

    driver.execute_script("arguments[0].click();", edit_btn)
    log.info("Opened Personal Details edit panel.")
    human_delay(2, 3)

    # Locate First Name input
    first_name_el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            "//input[@name='firstName'] | //input[@placeholder='First Name'] | //input[@id='firstName']"
        ))
    )

    current_name = first_name_el.get_attribute("value") or ""
    log.info(f"Current first name: '{current_name}'")

    # Toggle trailing space
    add_space = read_toggle_state()
    new_name  = (current_name.rstrip() + " ") if add_space else current_name.rstrip()
    action    = "Adding trailing space" if add_space else "Removing trailing space"
    log.info(f"{action} → new value: '{new_name}'")

    first_name_el.click()
    human_delay(0.5, 1)
    first_name_el.send_keys(Keys.CONTROL + "a")
    first_name_el.send_keys(Keys.DELETE)
    human_delay(0.3, 0.7)
    first_name_el.send_keys(new_name)
    human_delay(1, 2)

    # Save
    save_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//button[normalize-space()='Save' or normalize-space()='save' or normalize-space()='SAVE']"
        ))
    )
    driver.execute_script("arguments[0].click();", save_btn)
    human_delay(3, 4)

    # Persist toggled state for next run
    write_toggle_state(not add_space)
    log.info("Profile timestamp refreshed ✓")
    log.info(f"Next run will: {'remove' if add_space else 're-add'} the space.")


def run():
    if not NAUKRI_EMAIL or not NAUKRI_PASSWORD:
        log.error("NAUKRI_EMAIL or NAUKRI_PASSWORD not set. Aborting.")
        raise SystemExit(1)

    log.info("=" * 60)
    log.info(f"  Naukri Auto-Updater  |  {datetime.now():%Y-%m-%d %H:%M:%S} UTC")
    log.info("=" * 60)

    driver = None
    try:
        driver = build_driver()
        login(driver)
        update_name_field(driver)
        log.info("Run completed successfully ✓")
    except Exception as e:
        log.error(f"Run failed: {e}", exc_info=True)
        raise SystemExit(1)
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    run()
