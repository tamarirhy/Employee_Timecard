from flask import Flask, render_template, request
from datetime import datetime, timedelta
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import os
from supabase import create_client, Client

load_dotenv()

app = Flask(__name__)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

START_DATE = datetime(2026, 6, 1)
PERIOD_LENGTH = 14
REMINDER_START = datetime(2026, 6, 25)


SETTINGS_FILE = "settings.json"

# SETTINGS(Employees/Employer)

def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        data = {}
    
    if "employees" not in data:
        data["employees"] = []

    if "email_password" not in data:
        data["email_password"] = ""

    if "employer" not in data:
        data["employer"] = ""

    return data

def save_settings(data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# DATE HELPERS
def get_week_dates(start_of_period):
    """
    Returns two weeks of Mon–Fri date labels
    """

    # find first Monday on/after start date
    start_week1 = start_of_period - timedelta(days=start_of_period.weekday())

    week1 = [start_week1 + timedelta(days=i) for i in range(5)]
    week2_start = start_week1 + timedelta(days=7)
    week2 = [week2_start + timedelta(days=i) for i in range(5)]

    return week1, week2

# PAY PERIOD

def get_current_pay_period(today=None):
    today = datetime.now()

    delta_days = (today - START_DATE).days

    period_index = delta_days // PERIOD_LENGTH

    period_start = START_DATE + timedelta(days=period_index * PERIOD_LENGTH)
    period_end = period_start + timedelta(days=PERIOD_LENGTH - 1)

    return period_start, period_end

# HOURS CALCULATIONS

def calculate_week(prefix, form):
    days = ["mon", "tue", "wed", "thu", "fri"]
    return sum( float(form.get(f"{prefix}_{day}", 0) or 0) for day in days)

# EMAIL TO EMPLOYER (SUBMISSION)

def save_timecard(data):
    try:
        response = (
            supabase.table("timecards")
            .insert(data)
            .execute()
        )

        print("Timecard saved successfully!")

        return True

    except Exception as e:
        print(f"Supabase Error: {e}")
        return False

#REMINDER EMAIL (SENT TO EMPLOYEES)

def send_reminder_email():
    print("Sending reminder email...")

    password = os.getenv("EMAIL_PASSWORD")

    employees = os.getenv("EMPLOYEES", "").split(",")
    employees = [e.strip() for e in employees if e.strip()]
    if not employees:
        print("No employee emails configured.")
        return
    sender = os.getenv("SENDER_EMAIL") #change to jana's email


    link = os.getenv("BASE_URL")

    html = f"""
    <h2>Timecard Reminder</h2>

    <p>This is a reminder to complete your timecard for the current pay period.</p>

    <p>
        Please submit your timecard here:
    </p>

    <a href="{link}"
       style="
        display:inline-block;
        padding:12px 18px;
        background:#7a003c;
        color:white;
        text-decoration:none;
        border-radius:8px;
        font-weight:bold;
       ">
        Open Timecard
    </a>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Timecard Reminder"
    msg["From"] = sender
    msg["To"] = ", ".join(employees)

    msg.attach(MIMEText(html, "html"))  

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
        server.login(sender, password)
        server.send_message(msg)


#ROUTE

@app.route("/", methods=["GET", "POST"])
def home():

    period_start, period_end = get_current_pay_period()
    week1, week2 = get_week_dates(period_start)

    if request.method == "POST":
        name = request.form.get("employee_name")

        week1_total = calculate_week("week1", request.form)
        week2_total = calculate_week("week2", request.form)
        total = week1_total + week2_total

        timecard = {
            "employee_name": name,
            "employee_email": request.form.get("employee_email"),
            "pay_period_start": period_start.strftime("%Y-%m-%d"),
            "pay_period_end": period_end.strftime("%Y-%m-%d"),

            "week1_mon": request.form.get("week1_mon"),
            "week1_tue": request.form.get("week1_tue"),
            "week1_wed": request.form.get("week1_wed"),
            "week1_thu": request.form.get("week1_thu"),
            "week1_fri": request.form.get("week1_fri"),

            "week2_mon": request.form.get("week2_mon"),
            "week2_tue": request.form.get("week2_tue"),
            "week2_wed": request.form.get("week2_wed"),
            "week2_thu": request.form.get("week2_thu"),
            "week2_fri": request.form.get("week2_fri"),

            "week1_total": week1_total,
            "week2_total": week2_total,
            "total_hours": total
}


        saved = save_timecard(timecard)

        if not saved:
            return "Failed to save timecard.", 500

        return render_template(
        "index.html",
        week1=week1,
        week2=week2,
        success=True
)
    return render_template(
        "index.html",
        week1=week1,
        week2=week2
    )

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False) 
