"""One-time YouTube OAuth via the device flow.

Stores the refresh token at private/yt_token.json (gitignored). Re-run any
time; it refreshes silently once a token exists.
"""

import json
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLIENT_SECRET = os.path.join(ROOT, "yt_api_key.json")
TOKEN_PATH = os.path.join(ROOT, "private", "yt_token.json")
SCOPES = ("https://www.googleapis.com/auth/youtube.upload "
          "https://www.googleapis.com/auth/youtube")


def main() -> int:
    with open(CLIENT_SECRET, encoding="utf-8") as fh:
        client = json.load(fh)["installed"]

    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, encoding="utf-8") as fh:
            tok = json.load(fh)
        resp = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "refresh_token": tok["refresh_token"],
            "grant_type": "refresh_token"}, timeout=30)
        if resp.ok:
            print("existing token still valid; access token refreshed OK")
            return 0
        print("stored token invalid (%s); starting new device flow"
              % resp.status_code)

    resp = requests.post("https://oauth2.googleapis.com/device/code", data={
        "client_id": client["client_id"], "scope": SCOPES}, timeout=30)
    if not resp.ok:
        print("device flow rejected: %s %s" % (resp.status_code, resp.text))
        return 1
    dev = resp.json()
    print("==> Open %s and enter code: %s"
          % (dev["verification_url"], dev["user_code"]), flush=True)

    deadline = time.time() + dev["expires_in"]
    interval = dev.get("interval", 5)
    while time.time() < deadline:
        time.sleep(interval)
        poll = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client["client_id"],
            "client_secret": client["client_secret"],
            "device_code": dev["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"},
            timeout=30)
        data = poll.json()
        if "access_token" in data:
            os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
            with open(TOKEN_PATH, "w", encoding="utf-8") as fh:
                json.dump({
                    "token": data["access_token"],
                    "refresh_token": data["refresh_token"],
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "client_id": client["client_id"],
                    "client_secret": client["client_secret"],
                    "scopes": SCOPES.split()}, fh, indent=1)
            print("token stored at %s" % TOKEN_PATH)
            return 0
        err = data.get("error", "")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 5
            continue
        print("device flow failed: %s" % data)
        return 1
    print("device code expired before authorization")
    return 1


if __name__ == "__main__":
    sys.exit(main())
