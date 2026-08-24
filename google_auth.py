from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


CREDENTIALS_FILE = Path(
    "/opt/expense-bot/secrets/google_credentials.json"
)

TOKEN_FILE = Path(
    "/opt/expense-bot/secrets/google_token.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/drive.file"
]


def main() -> None:
    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_FILE,
        SCOPES,
    )

    credentials = flow.run_local_server(
        host="localhost",
        port=8080,
        open_browser=False,
        access_type="offline",
        prompt="consent",
    )

    TOKEN_FILE.write_text(
        credentials.to_json(),
        encoding="utf-8",
    )

    print(
        f"Token saved: {TOKEN_FILE}"
    )


if __name__ == "__main__":
    main()
