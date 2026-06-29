import os
import smtplib
from email.message import EmailMessage
from typing import List, Tuple


DEFAULT_SMTP_HOST = "127.0.0.1"
DEFAULT_SMTP_PORT = 3025
DEFAULT_SMTP_USER = "student"
DEFAULT_SMTP_PASSWORD = "password"
DEFAULT_SMTP_FROM = "monitoring@aeroairlines.com"


def _is_enabled() -> bool:
    return os.getenv("SMTP_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}


def _parse_recipients(value: str) -> List[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _get_recipients() -> List[str]:
    configured = os.getenv("EMAIL_RECIPIENTS", "enrico@eduvos.com")
    return _parse_recipients(configured)


def build_email_content(payload: dict) -> Tuple[str, str]:
    flight_number = payload.get("flight_number", "UNKNOWN")
    error_type = payload.get("triggered_parameter", payload.get("new_error_type", "Unknown Error"))
    recorded_value = payload.get("recorded_value")
    timestamp = payload.get("timestamp")
    issue_description = payload.get("issue_description", payload.get("new_error_message", "No description provided."))

    subject = f"ALERT: {error_type} Violation (Flight {flight_number})"

    active_lines = []
    for incident in payload.get("active_errors_for_flight", []):
        active_lines.append(
            f"- {incident.get('error_type', 'Unknown')}: {incident.get('message', '')} (first_detected={incident.get('first_detected', '')})"
        )

    if not active_lines:
        active_lines.append("- None")

    if error_type == "Cabin Pressure":
        value_text = f"{recorded_value} PSI" if recorded_value is not None else "N/A"
    else:
        value_text = str(recorded_value) if recorded_value is not None else "N/A"

    action_recipients = ", ".join(_get_recipients())

    body = (
        "Aero Airlines Flight Safety Monitoring Alert\n\n"
        f"Parameter: {error_type}\n"
        f"Recorded Value: {value_text}\n"
        f"Timestamp: {timestamp}\n"
        f"Issue Description: {issue_description}\n"
        f"Flight Number: {flight_number}\n"
        f"Simple Status: {payload.get('simple_status')}\n"
        f"Action: Email notification sent to {action_recipients}\n\n"
        "Active Errors For Flight:\n"
        f"{'\n'.join(active_lines)}\n"
    )

    return subject, body


def send_email_notification(subject: str, body: str) -> Tuple[bool, str]:
    if not _is_enabled():
        return True, "SMTP_DISABLED"

    recipients = _get_recipients()
    if not recipients:
        return False, "No recipients configured in EMAIL_RECIPIENTS"

    smtp_host = os.getenv("SMTP_HOST", DEFAULT_SMTP_HOST)
    smtp_port = int(os.getenv("SMTP_PORT", str(DEFAULT_SMTP_PORT)))
    smtp_user = os.getenv("SMTP_USER", DEFAULT_SMTP_USER)
    smtp_password = os.getenv("SMTP_PASSWORD", DEFAULT_SMTP_PASSWORD)
    smtp_from = os.getenv("SMTP_FROM", DEFAULT_SMTP_FROM)
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "false").strip().lower() in {"1", "true", "yes", "on"}
    smtp_require_auth = os.getenv("SMTP_REQUIRE_AUTH", "false").strip().lower() in {"1", "true", "yes", "on"}
    smtp_debug = os.getenv("SMTP_DEBUG", "false").strip().lower() in {"1", "true", "yes", "on"}

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = smtp_from
    message["To"] = ", ".join(recipients)
    message.set_content(body)

    try:
        with smtplib.SMTP(host=smtp_host, port=smtp_port, timeout=10) as client:
            if smtp_debug:
                # Mirrors the guide's smtp.set_debuglevel(1) for transport visibility.
                client.set_debuglevel(1)

            if smtp_use_tls:
                client.starttls()

            if smtp_require_auth:
                client.login(smtp_user, smtp_password)

            client.send_message(message)

        return True, f"sent_to={','.join(recipients)} smtp={smtp_host}:{smtp_port}"
    except Exception as exc:
        return False, str(exc)
