import schedule
import time
from datetime import datetime
from collections import deque
from email.mime.text import MIMEText
import smtplib
import traceback
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
from playwright.sync_api import sync_playwright

import subprocess
import sys

def install_playwright_dependencies():
    try:
        print("Installing Playwright dependencies...")
        # Try installing Playwright dependencies
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "libx11-xcb1", "libnss3", "libatk-bridge2.0-0", "libgtk-3-0", "libgbm1", "-y"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {str(e)}")
        raise

install_playwright_dependencies()



class TPOMonitor:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.latest_companies = deque()
        self.browser = None
        self.page = None
        self.is_first_run = True

    def initialize_browser(self):
        try:
            # Install Playwright and its dependencies
            os.system("playwright install-deps")
            print("Playwright installed successfully!")

            if self.browser:
                self.browser.close()

            # Start the browser
            playwright = sync_playwright().start()
            self.browser = playwright.chromium.launch(headless=True)
            self.page = self.browser.new_page()
            self.login()

        except Exception as e:
            print(f"Error initializing browser: {str(e)}")
            traceback.print_exc()
            raise

    def login(self):
        try:
            print(f"\n[{datetime.now()}] Logging in to TPO portal...")
            self.page.goto("https://tpo.vierp.in")

            self.page.fill("input[placeholder='Enter Your Username']", self.username)
            self.page.fill("input[placeholder='Enter Your Password']", self.password)
            self.page.click("button.logi")

            self.page.wait_for_url("**/home", timeout=10000)
            print("Login successful!")

        except Exception as e:
            print(f"Login failed: {str(e)}")
            traceback.print_exc()
            raise

    def get_current_companies(self):
        try:
            self.page.goto("https://tpo.vierp.in/company-dashboard")
            self.page.wait_for_selector("table", timeout=10000)

            company_rows = self.page.query_selector_all("table tbody tr")
            current_companies = [
                row.query_selector("td:nth-child(1)").inner_text() for row in company_rows[:10]
            ]
            return current_companies

        except Exception as e:
            print(f"Error getting companies: {str(e)}")
            traceback.print_exc()
            raise

    def send_alert_email(self, new_companies):
        try:
            email_from = os.getenv("EMAIL_FROM")
            email_to = os.getenv("EMAIL_TO").split(",")
            email_password = os.getenv("EMAIL_PASSWORD")

            current_time = datetime.now().strftime("%d-%b %I:%M %p")
            email_subject = f"New Companies Alert - {current_time}"

            email_body = "Hello,\n\nNew companies have been posted on the TPO portal:\n\n"
            for i, company in enumerate(new_companies, 1):
                email_body += f"{i}. {company}\n"

            email_body += "\nPlease check the portal for more details.\n\nBest regards,\nTPO Alert System"

            msg = MIMEText(email_body)
            msg['Subject'] = email_subject
            msg['From'] = email_from
            msg['To'] = ", ".join(email_to)

            smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            smtp_server.login(email_from, email_password)
            smtp_server.send_message(msg)
            smtp_server.quit()

            print(f"Alert email sent for {len(new_companies)} new companies")

        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            traceback.print_exc()

    def check_for_updates(self):
        try:
            print(f"\n[{datetime.now()}] Checking for new companies...")
            current_companies = self.get_current_companies()

            if self.is_first_run:
                self.latest_companies = deque(current_companies)
                self.is_first_run = False
                print("Initial company list stored")
                return

            # Compare current companies with stored ones
            new_companies = [company for company in current_companies if company not in self.latest_companies]

            if new_companies:
                print(f"Found {len(new_companies)} new companies!")
                self.send_alert_email(new_companies)
                self.latest_companies = deque(current_companies)
            else:
                print("No new companies found")

        except Exception as e:
            print(f"Error during update check: {str(e)}")
            traceback.print_exc()

    def run_monitor(self):
        print("Starting TPO Monitor...")
        try:
            self.initialize_browser()

            schedule.every(30).minutes.do(self.check_for_updates)

            self.check_for_updates()

            while True:
                schedule.run_pending()
                time.sleep(1)

        except Exception as e:
            print(f"Error in run_monitor: {str(e)}")
            traceback.print_exc()
            if self.browser:
                self.browser.close()


# Automatically start monitoring when deployed
if __name__ == "__main__":
    username = os.getenv("TPO_USERNAME")
    password = os.getenv("TPO_PASSWORD")
    monitor = TPOMonitor(username, password)
    monitor.run_monitor()
