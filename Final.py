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


class TPOMonitor:

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.latest_companies = deque()
        self.browser = None
        self.page = None
        self.is_first_run = True
        self.is_running = False

    def initialize_browser(self):
        try:
            # Ensure Playwright browsers are installed
            os.system("playwright install")
            
            if self.browser:
                self.browser.close()
    
            playwright = sync_playwright().start()
            
            # Launch the browser with --no-sandbox flag to bypass sandboxing issues
            self.browser = playwright.chromium.launch(headless=True, args=["--no-sandbox"])
            self.page = self.browser.new_page()
    
            # Check if the page is successfully created
            if self.page is None:
                raise Exception("Failed to create page object")

            self.login()
        except Exception as e:
            print(f"Error initializing browser: {e}")
            self.page = None  # Explicitly set page to None if there's an error


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
            if self.page is None:
                print("Browser page is not initialized.")
                return []
    
            self.page.goto("https://tpo.vierp.in/company-dashboard")
            # Continue with your scraping logic here...
        except Exception as e:
            print(f"Error while navigating: {e}")
            return []


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

            # Call session recovery
            try:
                self.recover_session()
            except Exception as recovery_error:
                print(f"Failed to recover session: {str(recovery_error)}")


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
    def recover_session(self):
        try:
            print(f"\n[{datetime.now()}] Attempting session recovery...")
            self.initialize_driver()  # Reinitialize the driver
            self.is_first_run = False  # Ensure it doesn’t reset the latest_companies
            print("Session recovered successfully!")
        except Exception as e:
            print(f"Session recovery failed: {str(e)}")
        traceback.print_exc()
        raise



# Automatically start monitoring when deployed
if __name__ == "__main__":
    username = os.getenv("TPO_USERNAME")
    password = os.getenv("TPO_PASSWORD")
    monitor = TPOMonitor(username, password)
    monitor.run_monitor()
