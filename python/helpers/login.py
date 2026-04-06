import hashlib

from python.helpers import dotenv, mos_auth


def get_credentials_hash():
    user = dotenv.get_dotenv_value("AUTH_LOGIN")
    password = dotenv.get_dotenv_value("AUTH_PASSWORD")
    if not user:
        return None
    return hashlib.sha256(f"{user}:{password}".encode()).hexdigest()


def is_login_required():
    if mos_auth.is_mos_auth_enabled():
        return True
    user = dotenv.get_dotenv_value("AUTH_LOGIN")
    return bool(user)
