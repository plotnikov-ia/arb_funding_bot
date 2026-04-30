import os
import requests
from dotenv import load_dotenv

from src.logging import LOG_ENABLED, log_event

load_dotenv()

INFISICAL_CLIENT_ID = os.getenv("INFISICAL_CLIENT_ID", "")
INFISICAL_CLIENT_SECRET = os.getenv("INFISICAL_CLIENT_SECRET", "")
INFISICAL_WORKSPACE_ID = os.getenv("INFISICAL_WORKSPACE_ID", "")


def get_access_token():
    try:
        LOG_ENABLED and log_event("infisical_client", action="request access token")
        res = requests.post(
            "https://app.infisical.com/api/v1/auth/universal-auth/login",
            json={
                "clientId": INFISICAL_CLIENT_ID,
                "clientSecret": INFISICAL_CLIENT_SECRET
            }, timeout=10
        )

        res.raise_for_status()
        data = res.json()
        token = data["accessToken"]
        LOG_ENABLED and log_event("infisical_client", action="access token received")
        return token

    except requests.RequestException:
        LOG_ENABLED and log_event("infisical_client", action="access token failed")
        pass


def get_secrets(token):
    try:
        LOG_ENABLED and log_event("infisical_client", action="fetch secrets")
        res = requests.get(
            "https://app.infisical.com/api/v3/secrets/raw",
            headers={
                "Authorization": f"Bearer {token}"
            },
            params={
                "workspaceId": INFISICAL_WORKSPACE_ID,
                "environment": "prod"
            }, timeout=10
        )

        res.raise_for_status()
        LOG_ENABLED and log_event("infisical_client", action="secrets received")
        return res.json()

    except requests.RequestException:
        LOG_ENABLED and log_event("infisical_client", action="secrets fetch failed")
        pass


class Secrets:
    def __init__(self):
        self._data = None

    def get(self, key):
        return self._data[key]
    
    def load_secrets(self):
        token = get_access_token()
        raw = get_secrets(token)

        self._data = {
            s["secretKey"]: s["secretValue"]
            for s in raw["secrets"]
        }