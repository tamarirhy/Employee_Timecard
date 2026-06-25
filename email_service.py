import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_reminder_email():
    print("Sending reminder email...")

    password = os.getenv("EMAIL_PASSWORD")
    sender = os.getenv("SENDER_EMAIL")

    employees = os.getenv("EMPLOYEES", "").split(",")
    employees = [e.strip() for e in employees if e.strip()]

    link = os.getenv("BASE_URL")

    html = f"""
    <h2>Timecard Reminder</h2>
    <p>Please submit your timecard here:</p>
    <a href="{link}">Open Timecard</a>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Timecard Reminder"
    msg["From"] = sender
    msg["To"] = ", ".join(employees)

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.send_message(msg)