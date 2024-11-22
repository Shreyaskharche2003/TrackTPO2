import schedule
import time
from datetime import datetime
from collections import deque
from email.mime.text import MIMEText
import smtplib
import traceback
import os
from dotenv import load_dotenv
from pyppeteer import launch
import asyncio
import streamlit as st

# Load environment variables from .env file
load_dotenv()

class TPOMonitor:

    def __init__(self):
        self.username = os.getenv("TPO_USERNAME")
        self.password = os.getenv("TPO_PASSWORD")
        self.latest_companies = deque()
        self.browser = None
        self.page = None
        self.is_first_run = True
        self.is_running = False

    async def initialize_browser(self):
        try:
            if self.browser:
                await self.browser.close()

            self.browser = await launch(headless=True)
            self.page = await self.browser.newPage()
            await self.login()

        except Exception as e:
            print(f"Error initializing browser: {str(e)}")
            traceback.print_exc()
            raise

    async def login(self):
        try:
            print(f"\n[{datetime.now()}] Logging in to TPO portal...")
            await self.page.goto("https://tpo.vierp.in")

            await self.page.type("input[placeholder='Enter Your Username']", self.username)
            await self.page.type("input[placeholder='Enter Your Password']", self.password)
            await self.page.click("button.logi")

            await self.page.waitForSelector("body", timeout=10000)
            print("Login successful!")

        except Exception as e:
            print(f"Login failed: {str(e)}")
            traceback.print_exc()
            raise

    async def get_current_companies(self):
        try:
            await self.page.goto("https://tpo.vierp.in/company-dashboard")

            await self.page.waitForSelector("table", timeout=10000)

            company_rows = await self.page.querySelectorAll("table tbody tr")
            current_companies = [
                await row.querySelectorEval("td:nth-child(1)", "el => el.innerText") for row in company_rows[:10]
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

    async def check_for_updates(self):
        try:
            print(f"\n[{datetime.now()}] Checking for new companies...")
            current_companies = await self.get_current_companies()

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
                await self.recover_session()
            except Exception as recovery_error:
                print(f"Failed to recover session: {str(recovery_error)}")

    async def run_monitor(self):
        print("Starting TPO Monitor...")
        try:
            await self.initialize_browser()

            schedule.every(30).minutes.do(lambda: asyncio.ensure_future(self.check_for_updates()))

            # Initial check
            await self.check_for_updates()

            while self.is_running:
                schedule.run_pending()
                await asyncio.sleep(1)

        except Exception as e:
            print(f"Error in run_monitor: {str(e)}")
            traceback.print_exc()
            if self.browser:
                await self.browser.close()

    async def recover_session(self):
        try:
            print(f"\n[{datetime.now()}] Attempting session recovery...")
            await self.initialize_browser()  # Reinitialize the browser
            self.is_first_run = False  # Ensure it doesn’t reset the latest_companies
            print("Session recovered successfully!")
        except Exception as e:
            print(f"Session recovery failed: {str(e)}")
            traceback.print_exc()
            raise


# Streamlit Integration
st.title("TPO Monitoring Dashboard")
st.markdown("""
This app allows you to monitor the TPO portal for updates and receive alerts for new companies.  
Use the buttons below to start or stop monitoring.
""")

monitor = TPOMonitor()

if "is_running" not in st.session_state:
    st.session_state.is_running = False

# Start Monitoring
if st.button("Start Monitoring") and not st.session_state.is_running:
    st.info("Starting the TPO monitor. Please wait...")
    try:
        st.session_state.is_running = True
        asyncio.run(monitor.run_monitor())
    except Exception as e:
        st.error(f"Error: {str(e)}")

# Stop Monitoring
if st.button("Stop Monitoring") and st.session_state.is_running:
    st.warning("Stopping the monitor...")
    try:
        monitor.is_running = False
        st.session_state.is_running = False
        if monitor.browser:
            asyncio.run(monitor.browser.close())
        st.success("Monitoring stopped.")
    except Exception as e:
        st.error(f"Error while stopping: {str(e)}")
