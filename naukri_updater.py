"""
Naukri Profile Auto-Updater — GitHub Actions Edition (Cookie-based login)
- Skips login form entirely — uses session cookies directly
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

# ── Session cookies from GitHub Secrets ───────────────────────────────────────
NAUK_SID      = os.environ.get("NAUK_SID", "")       # nauk_sid  (auth token)
NAUK_RT       = os.environ.get("NAUK_RT", "")        # nauk_rt   (refresh token)
NAUK_OTL      = os.environ.get("NAUK_OTL", "")       # nauk_otl
NAUK_NKWAP    = os.environ.get("NAUK_NKWAP", "")     # NKWAP
NAUK_UNID     = os.environ.get("NAUK_UNID", "")      # MYNAUKRI[UNID]
NAUK_J        = os.environ.get("NAUK_J", "0")        # J

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toggle_state.txt")


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


def inject_cookies(driver):
    """
    Inject session cookies directly — bypasses login form and OTP entirely.
    Must navigate to naukri.com first before setting cookies (same-domain rule).
    """
    log.info("Injecting session cookies …")

    # Must be on naukri.com domain before setting cookies
    driver.get("https://www.naukri.com")
    human_delay(2, 3)

    cookies = [
        {"name": "nauk_sid",        "value": NAUK_SID,   "domain": ".naukri.com", "path": "/", "secure": True},
        {"name": "nauk_rt",         "value": NAUK_RT,    "domain": ".naukri.com", "path": "/", "secure": True},
        {"name": "nauk_otl",        "value": NAUK_OTL,   "domain": ".naukri.com", "path": "/", "secure": True},
        {"name": "NKWAP",           "value": NAUK_NKWAP, "domain": ".naukri.com", "path": "/", "secure": True},
        {"name": "MYNAUKRI[UNID]",  "value": NAUK_UNID,  "domain": ".naukri.com", "path": "/", "secure": True},
        {"name": "J",               "value": NAUK_J,     "domain": ".naukri.com", "path": "/", "secure": True},
    ]

    for cookie in cookies:
        if cookie["value"]:
            driver.add_cookie(cookie)
            log.info(f"Cookie set: {cookie['name']} ✓")
        else:
            log.warning(f"Cookie skipped (empty secret): {cookie['name']}")

    # Refresh so cookies take effect
    driver.refresh()
    human_delay(3, 4)

    log.info(f"URL after cookie inject: {driver.current_url}")
    driver.save_screenshot("after_cookie.png")

    # Verify we are logged in by checking for profile-related element
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//a[contains(@href,'mnjuser/profile')] | //div[contains(@class,'nI-gNb-drawer')]"
            ))
        )
        log.info("Session valid — logged in via cookies ✓")
    except TimeoutException:
        driver.save_screenshot("login_failed.png")
        raise RuntimeError(
            "Cookie login failed — session may have expired. "
            "Re-export cookies from your browser and update GitHub Secrets."
        )


def update_name_field(driver):
    log.info("Opening profile page …")
    driver.get("https://www.naukri.com/mnjuser/profile")
    human_delay(5, 7)

    log.info(f"Profile page URL: {driver.current_url}")
    driver.save_screenshot("profile_loaded.png")

    # ── Step 1: Find & click the Edit button for Personal Details ─────────────
    # Try multiple XPath patterns — Naukri's class names change over time
    edit_xpaths = [
        # Current Naukri UI (2024-2025)
        "//div[contains(@class,'widgetHead') and .//*[contains(text(),'Personal')]]//span[contains(@class,'edit')]",
        "//div[contains(@class,'widgetHead') and .//*[contains(text(),'Personal')]]//button",
        # Generic edit icons near "Personal Details" heading
        "//*[contains(text(),'Personal Details')]/ancestor::div[1]//*[contains(@class,'edit')]",
        "//*[contains(text(),'Personal Details')]/following::span[contains(@class,'edit')][1]",
        "//*[contains(text(),'Personal Details')]/following::button[contains(@class,'edit')][1]",
        # Broadest fallback — any edit pencil icon on page
        "//span[contains(@class,'editIcon')]",
        "//span[@title='Edit']",
        "//i[contains(@class,'edit')]",
    ]

    edit_btn = None
    for xpath in edit_xpaths:
        try:
            edit_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            log.info(f"Edit button found with: {xpath}")
            break
        except TimeoutException:
            continue

    if edit_btn is None:
        driver.save_screenshot("edit_btn_not_found.png")
        raise RuntimeError(
            "Could not find Personal Details edit button. "
            "Check edit_btn_not_found.png artifact for current page layout."
        )

    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", edit_btn)
    human_delay(0.5, 1)
    driver.execute_script("arguments[0].click();", edit_btn)
    log.info("Clicked Personal Details edit button.")
    human_delay(2, 3)
    driver.save_screenshot("after_edit_click.png")

    # ── Step 2: Find the First Name input ─────────────────────────────────────
    name_xpaths = [
        "//input[@name='firstName']",
        "//input[@id='firstName']",
        "//input[@placeholder='First Name']",
        "//input[@placeholder='Enter first name']",
        "//label[contains(text(),'First')]/following::input[1]",
    ]

    first_name_el = None
    for xpath in name_xpaths:
        try:
            first_name_el = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            )
            log.info(f"First name input found with: {xpath}")
            break
        except TimeoutException:
            continue

    if first_name_el is None:
        driver.save_screenshot("firstname_not_found.png")
        raise RuntimeError(
            "Could not find First Name input. "
            "Check firstname_not_found.png artifact for current page layout."
        )

    current_name = first_name_el.get_attribute("value") or ""
    log.info(f"Current first name: '{current_name}'")

    add_space = read_toggle_state()
    new_name  = (current_name.rstrip() + " ") if add_space else current_name.rstrip()
    log.info(f"{'Adding' if add_space else 'Removing'} trailing space → '{new_name}'")

    # Clear and type new value
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", first_name_el)
    first_name_el.click()
    human_delay(0.3, 0.6)
    first_name_el.send_keys(Keys.CONTROL + "a")
    first_name_el.send_keys(Keys.DELETE)
    human_delay(0.3, 0.5)
    first_name_el.send_keys(new_name)
    human_delay(1, 2)

    # ── Step 3: Save ──────────────────────────────────────────────────────────
    save_xpaths = [
        "//button[normalize-space()='Save']",
        "//button[normalize-space()='SAVE']",
        "//button[normalize-space()='save']",
        "//button[contains(@class,'save') and not(@disabled)]",
        "//input[@type='submit' and (contains(@value,'Save') or contains(@value,'SAVE'))]",
    ]

    save_btn = None
    for xpath in save_xpaths:
        try:
            save_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            log.info(f"Save button found with: {xpath}")
            break
        except TimeoutException:
            continue

    if save_btn is None:
        driver.save_screenshot("save_btn_not_found.png")
        raise RuntimeError(
            "Could not find Save button. "
            "Check save_btn_not_found.png artifact for current page layout."
        )

    driver.execute_script("arguments[0].click();", save_btn)
    human_delay(3, 4)
    driver.save_screenshot("after_save.png")

    write_toggle_state(not add_space)
    log.info("Profile timestamp refreshed ✓")
    log.info(f"Next run will: {'remove' if add_space else 're-add'} the space.")


def run():
    if not NAUK_SID:
        log.error("NAUK_SID secret not set. Aborting.")
        raise SystemExit(1)

    log.info("=" * 60)
    log.info(f"  Naukri Auto-Updater  |  {datetime.now():%Y-%m-%d %H:%M:%S} UTC")
    log.info("=" * 60)

    driver = None
    try:
        driver = build_driver()
        inject_cookies(driver)
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
