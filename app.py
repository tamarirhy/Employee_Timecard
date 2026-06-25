from flask import Flask, render_template, request
from datetime import datetime, timedelta
import smtplib
import json
import threading
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

scheduler = BackgroundScheduler()

#temp emails

EMPLOYEES = ["sanaa414@icloud.com"] 
EMPLOYER_EMAIL = "mrsjanapollard@gmail.com" 
EMAIL_PASSWORD = "evjk xbid xepl ljrw" 
SENDER_EMAIL = "mrsjanapollard@gmail.com"

START_DATE = datetime(2026, 6, 1)
PERIOD_LENGTH = 14
REMINDER_START = datetime(2026, 6, 25)


SETTINGS_FILE = "settings.json"

# SETTINGS(Employees/Employer)

def load_settings():
    with open(SETTINGS_FILE, "r") as f:
        data = json.load(f)

    data.setdefault("employees", [])
    data.setdefault("employer", "")
    data.setdefault("email_password", "")

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
    try:
        print("Sending email...")

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = SENDER_EMAIL
        msg["To"] = EMPLOYER_EMAIL

        with smtplib.SMTP_SSL("smtp.gmail.com", 587, timeout=10) as server:
            server.starttls()
            server.login(SENDER_EMAIL, EMAIL_PASSWORD)
            server.send_message(msg)

        print("Email sent successfully")

    except Exception as e:
        print("EMAIL ERROR:", e)

#REMINDER EMAIL (SENT TO EMPLOYEES)

def send_reminder_email():
    print("Sending reminder email...")

    if not EMAIL_PASSWORD:
        print("Missing EMAIL_PASSWORD")
        return

    if not EMPLOYEES:
        print("No employees listed")
        return

    link = "https://employee-timecard-cqde.onrender.com"

    html = f"""
    <h2>Timecard Reminder</h2>
    <p>Please complete your timecard.</p>

    <a href="{link}">
        Open Timecard
    </a>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Timecard Reminder"
    msg["From"] = SENDER_EMAIL
    msg["To"] = ", ".join(EMPLOYEES)  # IMPORTANT for Gmail compatibility

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 587, timeout=10) as server:
        server.starttls()
        server.login(SENDER_EMAIL, EMAIL_PASSWORD)
        server.sendmail(
            SENDER_EMAIL,
            EMPLOYEES,
            msg.as_string()
        )

    print("Reminder email sent!")
    print("EMAIL PASSWORD EXISTS:", bool(EMAIL_PASSWORD))
    print("EMPLOYEES:", EMPLOYEES)

# ONLY RUN EVERY OTHER THURSDAY

def send_if_payday():

    today = datetime.now().date()

    delta_days = (today - REMINDER_START.date()).days

    if delta_days % 14 == 0:
        send_reminder_email()

#SCHEDULER

scheduler.add_job(
    send_if_payday,
    trigger="cron",
    day_of_week="thu",
    hour=14
)

#ROUTE

@app.route("/", methods=["GET", "POST"])
def home():
    try:
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

        
            threading.Thread(target=send_email,args=("New Timecard Submission", email_body)).start()

            return render_template(
            "index.html",
            week1=week1,
            week2=week2,
            success=True
        )
        return render_template(
        "index.html",
        week1=week1,
        week2=week2)
    
    except Exception as e:
        print("FLASK ERROR:")
        traceback.print_exc()
        return "Server Error", 500


@app.route("/test-reminder")
def test_reminder():
    print("TEST TRIGGER: sending reminder email now")

    threading.Thread(target=send_reminder_email).start()

    return "Email triggered (background)"

#RUN APP

if __name__ == '__main__':
    scheduler.start()
    app.run(debug=True) 

