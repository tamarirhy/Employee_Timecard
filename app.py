from flask import Flask, render_template, request
from datetime import datetime, timedelta
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

scheduler = BackgroundScheduler()


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

def send_email(subject, body):
    settings = load_settings()

    password = os.getenv("EMAIL_PASSWORD")

    employer = os.getenv("EMPLOYER_EMAIL")
    sender = os.getenv("SENDER_EMAIL")#change to jana's email
    
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = employer

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)

#REMINDER EMAIL (SENT TO EMPLOYEES)

def send_reminder_email():
    print("Sending reminder email...")

    settings = load_settings()
    password = os.getenv("EMAIL_PASSWORD")

    employees = settings.get("employees", [])
    sender = os.getenv("SENDER_EMAIL") #change to jana's email


    link = "http://127.0.0.1:5000/" #later replace with live URL

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

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)

# ONLY RUN EVERY OTHER THURSDAY

def send_if_payday():

    today = datetime.now()

    delta_days = (today - REMINDER_START).days

    if delta_days % 14 == 0:
        send_reminder_email()

#SCHEDULER

scheduler.add_job(
    #send_if_payday,
    #trigger="cron",
    #day_of_week="thu",
    #hour=9
    send_reminder_email,
    trigger="interval",
    minutes=2

)

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

        email_body = f"""
    Employee: {name}
    EmployeeEmail: {request.form.get("employee_email")}

    Pay Period: {period_start.strftime("%Y-%m-%d")} to {period_end.strftime("%Y-%m-%d")}

    WEEK 1
    Monday: {request.form.get('week1_mon')}
    Tuesday: {request.form.get('week1_tue')}
    Wednesday: {request.form.get('week1_wed')}
    Thursday: {request.form.get('week1_thu')}
    Friday: {request.form.get('week1_fri')}
    Total: {week1_total}

    WEEK 2  
    Monday: {request.form.get('week2_mon')}
    Tuesday: {request.form.get('week2_tue')}
    Wednesday: {request.form.get('week2_wed')}
    Thursday: {request.form.get('week2_thu')}
    Friday: {request.form.get('week2_fri')}
    Total: {week2_total}

    
    Total Hours: {total}
    """

        send_email("New Timecard Submission", email_body)

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

#RUN APP

if __name__ == '__main__':
    scheduler.start()
    app.run(debug=True, use_reloader=False) 
