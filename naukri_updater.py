"""
Naukri Profile Auto-Updater — GitHub Actions Edition
- Uses Chromium + chromedriver installed via apt (perfectly version-matched)
- Updates First Name field to refresh "Last Updated" timestamp
- Toggles trailing space each run
"""

import os
import time
import random
import logging
import subprocess
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

NAUKRI_EMAIL    = os.environ.get("NAUKRI_EMAIL", "")
NAUKRI_PASSWORD = os.environ.get("NAUKRI_PASSWORD", "")
STATE_FILE      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toggle_state.txt")


def human_delay(min_s=1.0, max_s=2.5):
    time.sleep(random.uniform(min_s, max_s))


def read_toggle_state() -> bool:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return f.read().strip() == "1"
    return True


def write_toggle_state(state: bool):
    with open(STATE_FILE, "w") as f:
        f.write("1" if state else "0")


def find_chromedriver() -> str:
    candidates = [
        "/usr/lib/chromium-browser/chromedriver",
        "/usr/bin/chromedriver",
        "/snap/bin/chromium.chromedriver",
    ]
    for path in candidates:
        if os.path.exists(path):
            log.info(f"Using chromedriver at: {path}")
            return path
    result = subprocess.run(["which", "chromedriver"], capture_output=True, text=True)
    if result.returncode == 0:
        path = result.stdout.strip()
        log.info(f"Using chromedriver at: {path}")
        return path
    raise FileNotFoundError("chromedriver not found.")


def find_chrome_binary() -> str:
    candidates = [
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/snap/bin/chromium",
        "/usr/bin/google-chrome",
    ]
    for path in candidates:
        if os.path.exists(path):
            log.info(f"Using Chrome binary at: {path}")
            return path
    raise FileNotFoundError("Chrome/Chromium binary not found.")


def build_driver() -> webdriver.Chrome:
    opts = Options()
    opts.binary_location = find_chrome_binary()
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
    service = Service(find_chromedriver())
    driver  = webdriver.Chrome(service=service, options=opts)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def login(driver):
    log.info("Navigating to Naukri login …")
    driver.get("https://www.naukri.com/nlogin/login")
    human_delay(3, 5)

    log.info(f"URL after load: {driver.current_url}")
    log.info(f"Page title: {driver.title}")

    email_el = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "usernameField"))
    )
    log.info("Email field found ✓")
    email_el.clear()
    human_delay(0.5, 1)
    email_el.send_keys(NAUKRI_EMAIL)
    log.info(f"Email entered: {NAUKRI_EMAIL[:4]}****")
    human_delay()

    pwd_el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "passwordField"))
    )
    log.info("Password field found ✓")
    pwd_el.clear()
    human_delay(0.5, 1)
    pwd_el.send_keys(NAUKRI_PASSWORD)
    log.info("Password entered ✓")
    human_delay()

    try:
        login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[contains(text(),'Login') or contains(text(),'login') or @type='submit']"
            ))
        )
        driver.execute_script("arguments[0].click();", login_btn)
        log.info("Login button clicked ✓")
    except Exception:
        pwd_el.send_keys(Keys.RETURN)
        log.info("Pressed Enter to submit ✓")

    human_delay(5, 7)

    driver.save_screenshot("login_failed.png")
    log.info(f"URL after login: {driver.current_url}")

    if "nlogin" in driver.current_url:
        raise RuntimeError("Login failed — check NAUKRI_EMAIL / NAUKRI_PASSWORD secrets.")

    log.info("Login successful ✓")

def update_name_field(driver):
    log.info("Opening profile page …")
    driver.get("https://www.naukri.com/mnjuser/profile")
    human_delay(4, 6)

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

    first_name_el = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.XPATH,
            "//input[@name='firstName'] | //input[@placeholder='First Name'] | //input[@id='firstName']"
        ))
    )

    current_name = first_name_el.get_attribute("value") or ""
    log.info(f"Current first name: '{current_name}'")

    add_space = read_toggle_state()
    new_name  = (current_name.rstrip() + " ") if add_space else current_name.rstrip()
    log.info(f"{'Adding' if add_space else 'Removing'} trailing space → '{new_name}'")

    first_name_el.click()
    human_delay(0.5, 1)
    first_name_el.send_keys(Keys.CONTROL + "a")
    first_name_el.send_keys(Keys.DELETE)
    human_delay(0.3, 0.7)
    first_name_el.send_keys(new_name)
    human_delay(1, 2)

    save_btn = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((
            By.XPATH,
            "//button[normalize-space()='Save' or normalize-space()='save' or normalize-space()='SAVE']"
        ))
    )
    driver.execute_script("arguments[0].click();", save_btn)
    human_delay(3, 4)

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
