
import keyring


SERVICE_NAME = "PersonalDashboard"


def save_credential(name: str, value: str) -> None:
    keyring.set_password(
        SERVICE_NAME,
        name,
        value
    )


def get_credential(name: str) -> str | None:
    return keyring.get_password(
        SERVICE_NAME,
        name
    )


def delete_credential(name: str) -> None:
    keyring.delete_password(
        SERVICE_NAME,
        name
    )
