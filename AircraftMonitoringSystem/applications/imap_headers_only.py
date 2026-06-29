import imaplib
import os

from dotenv import load_dotenv


load_dotenv()


def main() -> None:
    host = os.getenv("IMAP_HOST", "localhost")
    port = int(os.getenv("IMAP_PORT", "3143"))
    user = os.getenv("IMAP_USER", "student")
    password = os.getenv("IMAP_PASSWORD", "password")

    mailbox = imaplib.IMAP4(host, port)
    try:
        mailbox.login(user, password)
        mailbox.select("INBOX", readonly=True)

        status, search_data = mailbox.search(None, "ALL")
        if status != "OK":
            print("SEARCH failed.")
            return

        message_ids = search_data[0].split()
        if not message_ids:
            print("No messages found.")
            return

        for msg_id in message_ids:
            status, data = mailbox.fetch(
                msg_id,
                "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT)])",
            )
            print(f"\nMessage {msg_id.decode(errors='replace')}")
            for item in data:
                if isinstance(item, tuple):
                    print(item[1].decode(errors="replace").strip())
    finally:
        mailbox.logout()


if __name__ == "__main__":
    main()
