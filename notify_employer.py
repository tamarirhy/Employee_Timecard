import os
import smtplib

# Used to create HTML emails
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Loads variables from the .env file
from dotenv import load_dotenv

# Used to connect to Supabase
from supabase import create_client, Client

# ---------------------------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------------------------

# Load the .env file
load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Gmail information
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Employer email
EMPLOYER_EMAIL = os.getenv("EMPLOYER_EMAIL")

# URL of your deployed Flask application
BASE_URL = os.getenv("BASE_URL")

# ---------------------------------------------------
# CONNECT TO SUPABASE
# ---------------------------------------------------

# Create a Supabase client that allows us to
# read and update the database.
supabase: Client = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

# ---------------------------------------------------
# SEND EMAIL
# ---------------------------------------------------

def send_email(timecard):
    """
    Sends one email notification to the employer
    for a newly submitted timecard.
    """

    # Create an email object
    msg = MIMEMultipart("alternative")

    # Email information
    msg["Subject"] = (
        f"New Timecard Submitted - "
        f"{timecard['employee_name']}"
    )

    msg["From"] = SENDER_EMAIL
    msg["To"] = EMPLOYER_EMAIL

    # Link to the employer dashboard
    dashboard_link = f"{BASE_URL}/admin"

    # HTML email
    html = f"""
    <html>

    <body
        style="
            font-family:Arial;
            background:#f4f4f4;
            padding:30px;
        ">

    <div
        style="
            max-width:600px;
            margin:auto;
            background:white;
            border-radius:10px;
            padding:30px;
            box-shadow:0 0 12px rgba(0,0,0,.15);
        ">

    <h2 style="color:#7a003c;">
        New Timecard Submitted
    </h2>

    <p>
        A new employee has submitted a timecard.
    </p>

    <hr>

    <p>
        <strong>Employee</strong><br>
        {timecard["employee_name"]}
    </p>

    <p>
        <strong>Email</strong><br>
        {timecard["employee_email"]}
    </p>

    <p>
        <strong>Pay Period</strong><br>

        {timecard["pay_period_start"]}

        -

        {timecard["pay_period_end"]}
    </p>

    <p>
        <strong>Week 1 Total</strong><br>

        {timecard["week1_total"]} hrs
    </p>

    <p>
        <strong>Week 2 Total</strong><br>

        {timecard["week2_total"]} hrs
    </p>

    <p>
        <strong>Total Hours</strong><br>

        {timecard["total_hours"]}
    </p>

    <br>

    <a
        href="{dashboard_link}"

        style="
            background:#7a003c;
            color:white;
            padding:14px 22px;
            text-decoration:none;
            border-radius:8px;
            font-weight:bold;
        ">

        View Dashboard

    </a>

    <br><br>

    <p
        style="
            color:gray;
            font-size:13px;
        ">

        This email was generated automatically by
        the Employee Timecard System.

    </p>

    </div>

    </body>

    </html>
    """

    # Attach the HTML to the email
    msg.attach(MIMEText(html, "html"))

    # Connect to Gmail using SSL
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:

        # Login to Gmail
        server.login(
            SENDER_EMAIL,
            EMAIL_PASSWORD
        )

        # Send the email
        server.send_message(msg)


# ---------------------------------------------------
# MAIN PROGRAM
# ---------------------------------------------------

def main():
    """
    Looks for every timecard that has not
    been emailed yet.
    """

    # Get every row where email_sent is False
    response = (
        supabase
        .table("timecards")
        .select("*")
        .eq("email_sent", False)
        .execute()
    )

    # Store the returned rows
    rows = response.data

    # Nothing to do
    if not rows:

        print("No new timecards found.")

        return

    print(
        f"Found {len(rows)} new submission(s)."
    )

    # Process each submission individually
    for row in rows:

        try:

            # Send the notification email
            send_email(row)

            # Update the database so this row
            # will not be emailed again.
            (
                supabase
                .table("timecards")
                .update(
                    {
                        "email_sent": True
                    }
                )
                .eq(
                    "id",
                    row["id"]
                )
                .execute()
            )

            print(
                f"Email sent for "
                f"{row['employee_name']}"
            )

        except Exception as e:

            # Print any error without stopping
            # the remaining emails.
            print(
                f"Failed for "
                f"{row['employee_name']}"
            )

            print(e)


# ---------------------------------------------------
# START PROGRAM
# ---------------------------------------------------

# This makes sure main() only runs when this file
# is executed directly.
if __name__ == "__main__":

    main()