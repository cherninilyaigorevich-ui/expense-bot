from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import (
    MediaFileUpload,
    MediaIoBaseDownload,
)

from io import BytesIO


TOKEN_FILE = Path(
    "/opt/expense-bot/secrets/google_token.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/drive.file"
]

EXPENSES_FOLDER_NAME = "expenses"
ARCHIVE_FILE_NAME = "family_expenses.xlsx"


def get_drive_service():
    """Создать авторизованный клиент Google Drive API."""

    credentials = Credentials.from_authorized_user_file(
        TOKEN_FILE,
        SCOPES,
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

        TOKEN_FILE.write_text(
            credentials.to_json(),
            encoding="utf-8",
        )

    return build(
        "drive",
        "v3",
        credentials=credentials,
    )


def find_folder(
    service,
    folder_name: str,
) -> str | None:
    """Найти папку в Google Drive по имени."""

    query = (
        "mimeType='application/vnd.google-apps.folder' "
        f"and name='{folder_name}' "
        "and trashed=false"
    )

    result = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            pageSize=10,
        )
        .execute()
    )

    files = result.get(
        "files",
        [],
    )

    if not files:
        return None

    return files[0]["id"]


def create_folder(
    service,
    folder_name: str,
) -> str:
    """Создать папку в Google Drive."""

    metadata = {
        "name": folder_name,
        "mimeType": (
            "application/vnd.google-apps.folder"
        ),
    }

    folder = (
        service.files()
        .create(
            body=metadata,
            fields="id",
        )
        .execute()
    )

    return folder["id"]


def get_or_create_expenses_folder(
    service,
) -> str:
    """Получить папку expenses или создать её."""

    folder_id = find_folder(
        service=service,
        folder_name=EXPENSES_FOLDER_NAME,
    )

    if folder_id is not None:
        return folder_id

    return create_folder(
        service=service,
        folder_name=EXPENSES_FOLDER_NAME,
    )


def find_file(
    service,
    folder_id: str,
    filename: str,
) -> str | None:
    """Найти файл внутри конкретной папки."""

    query = (
        f"'{folder_id}' in parents "
        f"and name='{filename}' "
        "and trashed=false"
    )

    result = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields="files(id, name)",
            pageSize=10,
        )
        .execute()
    )

    files = result.get(
        "files",
        [],
    )

    if not files:
        return None

    return files[0]["id"]


def upload_new_file(
    service,
    folder_id: str,
    local_file: Path,
) -> str:
    """Загрузить новый XLSX в Google Drive."""

    metadata = {
        "name": ARCHIVE_FILE_NAME,
        "parents": [
            folder_id,
        ],
    }

    media = MediaFileUpload(
        str(local_file),
        mimetype=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        resumable=True,
    )

    result = (
        service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id",
        )
        .execute()
    )

    return result["id"]


def update_existing_file(
    service,
    file_id: str,
    local_file: Path,
) -> None:
    """Обновить содержимое существующего XLSX."""

    media = MediaFileUpload(
        str(local_file),
        mimetype=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        resumable=True,
    )

    (
        service.files()
        .update(
            fileId=file_id,
            media_body=media,
        )
        .execute()
    )


def upload_or_update_archive(
    local_file: Path,
) -> str:
    """Загрузить новый архив или обновить существующий."""

    service = get_drive_service()

    folder_id = get_or_create_expenses_folder(
        service
    )

    file_id = find_file(
        service=service,
        folder_id=folder_id,
        filename=ARCHIVE_FILE_NAME,
    )

    if file_id is None:
        return upload_new_file(
            service=service,
            folder_id=folder_id,
            local_file=local_file,
        )

    update_existing_file(
        service=service,
        file_id=file_id,
        local_file=local_file,
    )

    return file_id


def download_archive(
    destination: Path,
) -> bool:
    """Скачать family_expenses.xlsx с Google Drive.

    Возвращает False, если файл ещё не существует.
    """

    service = get_drive_service()

    folder_id = get_or_create_expenses_folder(
        service
    )

    file_id = find_file(
        service=service,
        folder_id=folder_id,
        filename=ARCHIVE_FILE_NAME,
    )

    if file_id is None:
        return False

    request = service.files().get_media(
        fileId=file_id
    )

    buffer = BytesIO()

    downloader = MediaIoBaseDownload(
        buffer,
        request,
    )

    done = False

    while not done:
        _, done = downloader.next_chunk()

    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_bytes(
        buffer.getvalue()
    )

    return True
