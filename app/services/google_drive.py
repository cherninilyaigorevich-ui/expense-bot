from io import BytesIO
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import (
    MediaFileUpload,
    MediaIoBaseDownload,
)


TOKEN_FILE = Path(
    "/opt/expense-bot/secrets/google_token.json"
)

SCOPES = [
    "https://www.googleapis.com/auth/drive.file"
]

EXPENSES_FOLDER_NAME = "expenses"
DATABASE_BACKUPS_FOLDER_NAME = "database_backups"

ARCHIVE_FILE_NAME = "family_expenses.xlsx"


def get_drive_service():
    """Создать авторизованный клиент Google Drive API."""

    credentials = Credentials.from_authorized_user_file(
        TOKEN_FILE,
        SCOPES,
    )

    if credentials.expired and credentials.refresh_token:
        credentials.refresh(
            Request()
        )

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
    """Найти папку в корне Google Drive."""

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
    """Создать папку в корне Google Drive."""

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


def find_folder_in_parent(
    service,
    parent_id: str,
    folder_name: str,
) -> str | None:
    """Найти вложенную папку внутри указанной папки."""

    query = (
        "mimeType='application/vnd.google-apps.folder' "
        f"and name='{folder_name}' "
        f"and '{parent_id}' in parents "
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


def create_folder_in_parent(
    service,
    parent_id: str,
    folder_name: str,
) -> str:
    """Создать вложенную папку."""

    metadata = {
        "name": folder_name,
        "mimeType": (
            "application/vnd.google-apps.folder"
        ),
        "parents": [
            parent_id,
        ],
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


def get_or_create_database_backups_folder(
    service,
) -> str:
    """Получить папку expenses/database_backups."""

    expenses_folder_id = (
        get_or_create_expenses_folder(
            service
        )
    )

    folder_id = find_folder_in_parent(
        service=service,
        parent_id=expenses_folder_id,
        folder_name=DATABASE_BACKUPS_FOLDER_NAME,
    )

    if folder_id is not None:
        return folder_id

    return create_folder_in_parent(
        service=service,
        parent_id=expenses_folder_id,
        folder_name=DATABASE_BACKUPS_FOLDER_NAME,
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
    """Загрузить новый XLSX-архив."""

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
    """Обновить существующий XLSX-файл."""

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
    """Создать или обновить family_expenses.xlsx."""

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
    """Скачать family_expenses.xlsx.

    Возвращает False, если архив ещё не существует.
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


def upload_file_to_folder(
    service,
    folder_id: str,
    local_file: Path,
) -> str:
    """Загрузить произвольный файл в папку Google Drive."""

    metadata = {
        "name": local_file.name,
        "parents": [
            folder_id,
        ],
    }

    media = MediaFileUpload(
        str(local_file),
        mimetype="application/octet-stream",
        resumable=True,
    )

    result = (
        service.files()
        .create(
            body=metadata,
            media_body=media,
            fields="id, name",
        )
        .execute()
    )

    return result["id"]


def list_files_in_folder(
    service,
    folder_id: str,
) -> list[dict]:
    """Получить список файлов в папке."""

    query = (
        f"'{folder_id}' in parents "
        "and trashed=false"
    )

    result = (
        service.files()
        .list(
            q=query,
            spaces="drive",
            fields=(
                "files("
                "id,"
                "name,"
                "createdTime,"
                "modifiedTime"
                ")"
            ),
            orderBy="createdTime desc",
            pageSize=100,
        )
        .execute()
    )

    return result.get(
        "files",
        [],
    )


def cleanup_old_backup_files(
    service,
    folder_id: str,
    keep: int = 7,
) -> list[str]:
    """Оставить только последние N backup-файлов."""

    files = list_files_in_folder(
        service=service,
        folder_id=folder_id,
    )

    deleted_files: list[str] = []

    if len(files) <= keep:
        return deleted_files

    for file_info in files[keep:]:
        service.files().delete(
            fileId=file_info["id"]
        ).execute()

        deleted_files.append(
            file_info["name"]
        )

    return deleted_files
