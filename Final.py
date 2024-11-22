import asyncio
from pyppeteer import launch
from dotenv import load_dotenv
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import traceback

# Load environment variables
load_dotenv()

class TPOMonitor:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.latest_companies = []
        self.browser = None
        self.page = None
        self.is_first_run = True
        self.is_running = False

    async def initialize_browser(self):
        try:
            # Launch the browser using Pyppeteer
            self.browser = await launch(headless=True)
            self.page = await self.browser.newPage()

            if self.page is None:
                raise Exception("Failed to create page object")

            await self.login()
        except Exception as e:
            print(f"Error initializing browser: {e}")
            self.page = None  # Explicitly set page to None if there's an error

    async def login(self):
        try:
            print(f"\n[{datetime.now()}] Logging in to TPO portal...")
            await self.page.goto("https://tpo.vierp.in")

            await self.page.type("input[placeholder='Enter Your Username']", self.username)
            await self.page.type("input[placeholder='Enter Your Password']", self.password)
            await self.page.click("button.logi")

            await self.page.waitForNavigation({"waitUntil": "domcontentloaded"})
            print("Login successful!")

        except Exception as e:
            print(f"Login failed: {str(e)}")
            traceback.print_exc()
            raise

    async def get_current_companies(self):
        try:
            if self.page is None:
                print("Browser page is not initialized.")
                return []

            await self.page.goto("https://tpo.vierp.in/company-dashboard")
            # Add your scraping logic here to get the list of companies

            return []  # Return a placeholder list (to be replaced with actual scraping logic)
        except Exception as e:
            print(f"Error while navigating: {e}")
            return []

    async def send_alert_email(self, new_companies):
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

    async def check_for_updates(self):
        try:
            print(f"\n[{datetime.now()}] Checking for new companies...")
            current_companies = await self.get_current_companies()

            if self.is_first_run:
                self.latest_companies = current_companies
                self.is_first_run = False
                print("Initial company list stored")
                return

            # Compare current companies with stored ones
            new_companies = [company for company in current_companies if company not in self.latest_companies]

            if new_companies:
                print(f"Found {len(new_companies)} new companies!")
                await self.send_alert_email(new_companies)
                self.latest_companies = current_companies
            else:
                print("No new companies found")

        except Exception as e:
            print(f"Error during update check: {str(e)}")
            traceback.print_exc()

    async def run_monitor(self):
        print("Starting TPO Monitor...")
        try:
            await self.initialize_browser()

            while True:
                await self.check_for_updates()
                await asyncio.sleep(1800)  # Wait for 30 minutes before checking again

        except Exception as e:
            print(f"Error in run_monitor: {str(e)}")
            traceback.print_exc()
            if self.browser:
                await self.browser.close()

# Automatically start monitoring when deployed
if __name__ == "__main__":
    username = os.getenv("TPO_USERNAME")
    password = os.getenv("TPO_PASSWORD")
    monitor = TPOMonitor(username, password)

    asyncio.run(monitor.run_monitor())
