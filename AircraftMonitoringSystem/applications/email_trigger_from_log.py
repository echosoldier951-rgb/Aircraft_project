import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from email_service import build_email_content, send_email_notification


load_dotenv()

LOG_PREFIX = "[EmailTrigger]"
POLL_INTERVAL_SECONDS = 1
RETRY_INTERVAL_SECONDS = int(os.getenv("EMAIL_RETRY_INTERVAL_SECONDS", "30"))
BODY_PREVIEW_MAX = int(os.getenv("EMAIL_BODY_PREVIEW_MAX", "220"))
SOURCE_LOG_FILE = Path(__file__).resolve().parents[1] / "TriggerNotifications.txt"
STATE_FILE = Path(__file__).resolve().parents[1] / ".email_trigger_state"


retry_not_before = 0.0


def log_message(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} {LOG_PREFIX} {message}")


def _one_line(value: str, max_len: int = 220) -> str:
    if value is None:
        return ""

    compact = " ".join(value.split())
    if len(compact) <= max_len:
        return compact

    return f"{compact[:max_len]}..."


def _format_recorded_value(payload: dict) -> str:
    parameter = payload.get("triggered_parameter", payload.get("new_error_type", "Unknown"))
    value = payload.get("recorded_value")

    if value is None:
        return "N/A"

    if parameter == "Cabin Pressure":
        return f"{value} PSI"

    return str(value)


def log_q3_alert_block(payload: dict, sent: bool, details: str) -> None:
    parameter = payload.get("triggered_parameter", payload.get("new_error_type", "Unknown"))
    value_text = _format_recorded_value(payload)
    timestamp = payload.get("timestamp", "N/A")
    issue_description = payload.get("issue_description", payload.get("new_error_message", "No description provided."))
    recipients = os.getenv("EMAIL_RECIPIENTS", "enrico@eduvos.com")

    log_message("Q3_ALERT_BEGIN")
    log_message(f"ALERT: {parameter} Violation")
    log_message(f"Value: {value_text}")
    log_message(f"Time: {timestamp}")
    log_message(f"Issue: {issue_description}")

    if sent:
        log_message(f"Action: Email notification sent to {recipients}")
    else:
        log_message(f"Action: Email notification failed for {recipients} ({details})")

    log_message("Q3_ALERT_END")


def _load_offset() -> int:
    if not STATE_FILE.exists():
        return 0

    try:
        raw = STATE_FILE.read_text(encoding="utf-8").strip()
        return int(raw) if raw else 0
    except Exception:
        return 0


def _save_offset(offset: int) -> None:
    STATE_FILE.write_text(str(offset), encoding="utf-8")


def _extract_notification_payload(line: str):
    marker = "NOTIFICATION "
    marker_index = line.find(marker)
    if marker_index < 0:
        return None

    json_part = line[marker_index + len(marker):].strip()
    if not json_part:
        return None

    try:
        payload = json.loads(json_part)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None

    return payload


def process_new_lines(last_offset: int) -> int:
    global retry_not_before

    if not SOURCE_LOG_FILE.exists():
        return last_offset

    with SOURCE_LOG_FILE.open("r", encoding="utf-8") as source:
        source.seek(last_offset)
        committed_offset = last_offset

        while True:
            line_start_offset = source.tell()
            line = source.readline()

            if not line:
                return committed_offset

            payload = _extract_notification_payload(line)
            if payload is None:
                committed_offset = source.tell()
                continue

            now = time.time()
            if now < retry_not_before:
                return line_start_offset

            subject, body = build_email_content(payload)
            recipients = os.getenv("EMAIL_RECIPIENTS", "enrico@eduvos.com")
            smtp_host = os.getenv("SMTP_HOST", "localhost")
            smtp_port = os.getenv("SMTP_PORT", "3025")

            log_message(
                f"EMAIL_ATTEMPT flight={payload.get('flight_number', 'UNKNOWN')} "
                f"error={payload.get('new_error_type', 'Unknown')} "
                f"to={recipients} smtp={smtp_host}:{smtp_port} "
                f"subject=\"{_one_line(subject, 140)}\""
            )

            sent, details = send_email_notification(subject, body)

            flight_number = payload.get("flight_number", "UNKNOWN")
            error_type = payload.get("new_error_type", "Unknown")
            body_preview = _one_line(body, BODY_PREVIEW_MAX)

            if sent:
                log_message(
                    f"EMAIL_SENT flight={flight_number} error={error_type} details={details} "
                    f"subject=\"{_one_line(subject, 140)}\" body_preview=\"{body_preview}\""
                )
                log_q3_alert_block(payload, True, details)
                retry_not_before = 0.0
                committed_offset = source.tell()
                continue

            retry_not_before = now + RETRY_INTERVAL_SECONDS
            log_message(
                f"EMAIL_FAILED flight={flight_number} error={error_type} details={details} "
                f"retry_in={RETRY_INTERVAL_SECONDS}s "
                f"subject=\"{_one_line(subject, 140)}\""
            )
            log_q3_alert_block(payload, False, details)

            # Keep the failed notification pending so it can be retried next cycle.
            return line_start_offset


def main() -> None:
    log_message(f"Watching {SOURCE_LOG_FILE} for NOTIFICATION entries")
    offset = _load_offset()

    if SOURCE_LOG_FILE.exists():
        file_size = SOURCE_LOG_FILE.stat().st_size
        if offset > file_size:
            offset = 0

    while True:
        try:
            offset = process_new_lines(offset)
            _save_offset(offset)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            log_message(f"EXCEPTION {exc}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
