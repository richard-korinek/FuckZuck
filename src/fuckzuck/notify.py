"""Notification module - email and SMS alerts."""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from fuckzuck.birthdays import Birthday


def _get_message(names: list[str]) -> str:
    """Build notification message."""
    if not names:
        return "No birthdays today."
    name_list = ", ".join(names)
    return f"Today's birthdays: {name_list} — follow up personally!"


def _send_email(
    to_email: str,
    subject: str,
    body: str,
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
) -> bool:
    """Send email via SMTP. Returns True if successful."""
    try:
        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email send failed: {e}")
        return False


def _send_sms(
    to_phone: str,
    body: str,
    *,
    account_sid: str,
    auth_token: str,
    from_phone: str,
) -> bool:
    """Send SMS via Twilio. Returns True if successful."""
    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        client.messages.create(
            body=body,
            from_=from_phone,
            to=to_phone,
        )
        return True
    except Exception as e:
        print(f"SMS send failed: {e}")
        return False


def notify_user(birthdays: list[Birthday]) -> tuple[bool, bool]:
    """
    Send email and SMS notifications to the user about today's birthdays.
    Returns (email_ok, sms_ok).
    """
    names = [b.name for b in birthdays]
    body = _get_message(names)

    email_ok = False
    sms_ok = False

    if os.environ.get("NOTIFY_EMAIL_ENABLED", "true").lower() in ("true", "1", "yes"):
        to_email = os.environ.get("NOTIFY_EMAIL")
        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER")
        smtp_pass = os.environ.get("SMTP_PASS")

        if to_email and smtp_user and smtp_pass:
            subject = "FuckZuck: Today's Birthdays"
            email_ok = _send_email(
                to_email,
                subject,
                body,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_pass=smtp_pass,
            )
        else:
            print("Email notification skipped: NOTIFY_EMAIL, SMTP_USER, SMTP_PASS required")

    if os.environ.get("NOTIFY_SMS_ENABLED", "true").lower() in ("true", "1", "yes"):
        to_phone = os.environ.get("NOTIFY_PHONE")
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_phone = os.environ.get("TWILIO_FROM")

        if to_phone and account_sid and auth_token and from_phone:
            # Truncate for SMS (160 chars)
            sms_body = body[:155] + "..." if len(body) > 158 else body
            sms_ok = _send_sms(
                to_phone,
                sms_body,
                account_sid=account_sid,
                auth_token=auth_token,
                from_phone=from_phone,
            )
        else:
            print("SMS notification skipped: NOTIFY_PHONE, TWILIO_* required")

    return (email_ok, sms_ok)
