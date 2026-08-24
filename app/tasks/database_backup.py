import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

from app.services.google_drive import (
    cleanup_old_backup_files,
    get_drive_service,
    get_or_create_database_backups_folder,
    upload_file_to_folder,
)


BACKUP_DIR = Path(
    "/opt/expense-bot/backups"
)

KEEP_BACKUPS = 7


def create_database_backup() -> Path:
    """Создать PostgreSQL backup в custom format."""

    BACKUP_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S"
    )

    backup_file = (
        BACKUP_DIR
        / f"expenses_{timestamp}.dump"
    )

    command = [
        "docker",
        "exec",
        "expense-postgres",
        "pg_dump",
        "-U",
        "expense_user",
        "-d",
        "expenses",
        "-Fc",
    ]

    with backup_file.open("wb") as file_handle:
        subprocess.run(
            command,
            stdout=file_handle,
            check=True,
        )

    if (
        not backup_file.exists()
        or backup_file.stat().st_size == 0
    ):
        raise RuntimeError(
            "Database backup file is empty."
        )

    return backup_file


def validate_database_backup(
    backup_file: Path,
) -> None:
    """Проверить, что pg_restore может прочитать dump."""

    command = [
        "docker",
        "exec",
        "-i",
        "expense-postgres",
        "pg_restore",
        "--list",
    ]

    with backup_file.open("rb") as file_handle:
        result = subprocess.run(
            command,
            stdin=file_handle,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=False,
        )

    if result.returncode != 0:
        error_text = result.stderr.decode(
            "utf-8",
            errors="replace",
        )

        raise RuntimeError(
            "Database backup validation failed: "
            f"{error_text}"
        )


async def main() -> None:
    backup_file: Path | None = None

    try:
        print(
            "Creating PostgreSQL backup..."
        )

        backup_file = create_database_backup()

        print(
            f"Backup created: {backup_file}"
        )

        print(
            f"Backup size: "
            f"{backup_file.stat().st_size} bytes"
        )

        print(
            "Validating PostgreSQL backup..."
        )

        validate_database_backup(
            backup_file
        )

        print(
            "Backup validation: OK"
        )

        service = get_drive_service()

        backup_folder_id = (
            get_or_create_database_backups_folder(
                service
            )
        )

        file_id = upload_file_to_folder(
            service=service,
            folder_id=backup_folder_id,
            local_file=backup_file,
        )

        print(
            "Backup uploaded successfully."
        )

        print(
            f"Google Drive file ID: {file_id}"
        )

        deleted_files = cleanup_old_backup_files(
            service=service,
            folder_id=backup_folder_id,
            keep=KEEP_BACKUPS,
        )

        if deleted_files:
            for filename in deleted_files:
                print(
                    f"Old backup removed: {filename}"
                )
        else:
            print(
                "No old backups to remove."
            )

    finally:
        if backup_file is not None:
            backup_file.unlink(
                missing_ok=True
            )

            print(
                "Local backup removed."
            )


if __name__ == "__main__":
    asyncio.run(main())
