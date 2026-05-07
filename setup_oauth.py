"""
One-time script to obtain a Gmail OAuth2 refresh token.

Run via Docker (no local Python needed):
    docker compose run --rm setup

The script prints a URL — open it in your browser, authorize,
then Google will redirect to http://localhost (which will fail to load — that's OK).
Copy the full URL from your browser's address bar and paste it back into the terminal.
"""

from urllib.parse import urlparse, parse_qs

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.modify",
]

REDIRECT_URI = "http://localhost"


def main():
    client_id = input("Enter GMAIL_CLIENT_ID: ").strip()
    client_secret = input("Enter GMAIL_CLIENT_SECRET: ").strip()

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": [REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    flow.redirect_uri = REDIRECT_URI

    auth_url, _ = flow.authorization_url(prompt="consent")
    print(f"\nOpen this URL in your browser:\n\n{auth_url}\n")
    print("After authorizing, Google will redirect to http://localhost (page won't load — that's OK).")
    print("Copy the FULL URL from your browser's address bar and paste it here.\n")

    redirected_url = input("Paste the full redirect URL: ").strip()

    parsed = urlparse(redirected_url)
    params = parse_qs(parsed.query)
    code = params.get("code", [None])[0]
    if not code:
        raise ValueError(f"Could not find 'code' in URL: {redirected_url}")

    flow.fetch_token(code=code)
    creds = flow.credentials

    print("\n--- Copy these values to your .env / easypanel ---")
    print(f"GMAIL_CLIENT_ID={client_id}")
    print(f"GMAIL_CLIENT_SECRET={client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()
