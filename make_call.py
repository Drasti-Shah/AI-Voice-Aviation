import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv
from twilio.rest import Client


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python make_call.py <E.164 phone number, e.g. +919724556935>")
        return 1

    to = sys.argv[1].strip()
    if not to.startswith("+"):
        print(f"error: number must be E.164 and start with '+', got: {to}")
        return 1

    load_dotenv()
    try:
        sid = os.environ["TWILIO_ACCOUNT_SID"]
        token = os.environ["TWILIO_AUTH_TOKEN"]
        from_number = os.environ["TWILIO_FROM_NUMBER"]
        raw = os.environ["PUBLIC_HOST"].strip()
        parsed = urlparse(raw if "://" in raw else f"//{raw}", scheme="", allow_fragments=False)
        public_host = parsed.netloc or raw.split("/", 1)[0]
    except KeyError as missing:
        print(f"error: missing env var {missing} in .env")
        return 1

    twiml_url = f"https://{public_host}/voice"
    print(f"[call] from={from_number}  to={to}")
    print(f"[call] twiml url={twiml_url}")

    client = Client(sid, token)
    call = client.calls.create(
        to=to,
        from_=from_number,
        url=twiml_url,
        record=True,
    )
    print(f"[call] queued. sid={call.sid}  status={call.status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
