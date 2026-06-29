import imaplib
import os
from email import message_from_bytes

from dotenv import load_dotenv


load_dotenv()


def get_config():
    host = os.getenv("IMAP_HOST", "127.0.0.1")
    port = int(os.getenv("IMAP_PORT", "3143"))
    user = os.getenv("IMAP_USER", "student")
    password = os.getenv("IMAP_PASSWORD", "secret")
    return host, port, user, password


def decode_payload(msg):
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
        return ""

    payload = msg.get_payload(decode=True)
    if payload:
        return payload.decode("utf-8", errors="replace")
    return ""


def main():
    host, port, user, password = get_config()

    with imaplib.IMAP4(host, port) as client:
        login_status, _ = client.login(user, password)
        print(f"LOGIN: {login_status}")

        list_status, folders = client.list()
        print(f"LIST: {list_status}")
        for folder in folders:
            print(f"FOLDER: {folder.decode('utf-8', errors='replace')}")

        select_status, select_data = client.select("INBOX", readonly=True)
        print(f"SELECT INBOX: {select_status} messages={select_data[0].decode('utf-8', errors='replace') if select_data else '0'}")

        search_status, search_data = client.search(None, "ALL")
        print(f"SEARCH ALL: {search_status}")

        if search_status != "OK" or not search_data:
            print("No messages found.")
            client.logout()
            return

        message_ids = [item for item in search_data[0].split() if item]
        print(f"MESSAGE IDS: {[item.decode('utf-8', errors='replace') for item in message_ids]}")

        if not message_ids:
            print("No messages found.")
            client.logout()
            return

        latest_id = message_ids[-1]

        header_status, header_data = client.fetch(latest_id, "(BODY.PEEK[HEADER])")
        print(f"FETCH HEADER: {header_status}")

        body_status, body_data = client.fetch(latest_id, "(BODY.PEEK[])")
        print(f"FETCH BODY: {body_status}")

        if body_status == "OK" and body_data and isinstance(body_data[0], tuple):
            raw_message = body_data[0][1]
            email_message = message_from_bytes(raw_message)
            subject = email_message.get("Subject", "")
            sender = email_message.get("From", "")
            recipients = email_message.get("To", "")
            text_body = decode_payload(email_message)

            print(f"SUBJECT: {subject}")
            print(f"FROM: {sender}")
            print(f"TO: {recipients}")
            print("BODY:")
            print(text_body)

        client.logout()


if __name__ == "__main__":
    main()
