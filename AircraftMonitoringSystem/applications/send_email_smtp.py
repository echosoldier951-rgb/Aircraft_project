import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv
import os


load_dotenv()


def main() -> None:
    message = EmailMessage()
    message["From"] = os.getenv("SMTP_FROM", "monitoring@aeroairlines.com")
    message["To"] = os.getenv("EMAIL_RECIPIENTS", "enrico@eduvos.com")
    message["Subject"] = "IMAP Practical Test Message"
    message.set_content(
        "Hello student,\n\n"
        "This message was sent using SMTP and will be read using IMAP.\n"
        "IMAP keeps the message on the server and lets us search, flag, and fetch it.\n\n"
        "Regards,\n"
        "Python SMTP Client"
    )

    smtp_host = os.getenv("SMTP_HOST", "localhost")
    smtp_port = int(os.getenv("SMTP_PORT", "3025"))
    smtp_require_auth = os.getenv("SMTP_REQUIRE_AUTH", "false").strip().lower() in {"1", "true", "yes", "on"}

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        smtp.set_debuglevel(1)

        if smtp_require_auth:
            smtp_user = os.getenv("SMTP_USER", "student")
            smtp_password = os.getenv("SMTP_PASSWORD", "password")
            smtp.login(smtp_user, smtp_password)

        smtp.send_message(message)

    print("E-mail sent successfully.")


if __name__ == "__main__":
    main()
