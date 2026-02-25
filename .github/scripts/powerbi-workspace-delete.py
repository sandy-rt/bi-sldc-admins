# delete_specific_workspaces.py
"""
Deletes exactly the specified Power BI / Fabric workspaces by name.
Used via GitHub Actions with full names provided as input.

Requires:
- Python 3.8+
- pip install requests
"""

import os
import requests
import logging
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ──── Read from environment variables ────
TENANT_ID     = os.getenv("AZURE_TENANT_ID")
CLIENT_ID     = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
WORKSPACES_TO_DELETE = os.getenv("WORKSPACES_TO_DELETE", "")

if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, WORKSPACES_TO_DELETE]):
    logger.error("Missing required environment variables")
    exit(1)


def get_access_token() -> str:
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    payload = {
        "client_id": CLIENT_ID,
        "scope": "https://analysis.windows.net/powerbi/api/.default",
        "client_secret": CLIENT_SECRET,
        "grant_type": "client_credentials"
    }

    resp = requests.post(url, data=payload)
    if resp.status_code != 200:
        logger.error(f"Authentication failed: {resp.status_code} - {resp.text}")
        exit(1)

    logger.info("Authentication successful")
    return resp.json()["access_token"]


def list_workspaces(token: str) -> List[dict]:
    url = "https://api.powerbi.com/v1.0/myorg/groups?$top=500"
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        logger.error(f"Failed to list workspaces: {resp.status_code} - {resp.text}")
        return []

    return resp.json().get("value", [])


def delete_workspace(token: str, workspace_id: str, name: str) -> bool:
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.delete(url, headers=headers)

    if resp.status_code in (200, 202, 204):
        logger.info(f"Deleted: {name} ({workspace_id})")
        return True
    elif resp.status_code == 404:
        logger.info(f"Already deleted: {name}")
        return True
    else:
        logger.error(f"Delete failed for '{name}': {resp.status_code} - {resp.text}")
        return False


def main():
    token = get_access_token()

    target_names = {n.strip() for n in WORKSPACES_TO_DELETE.split(",") if n.strip()}
    if not target_names:
        logger.error("No workspace names provided")
        return

    logger.info(f"Workspaces targeted for deletion: {', '.join(sorted(target_names))}")

    all_ws = list_workspaces(token)
    if not all_ws:
        logger.info("No workspaces accessible or API error")
        return

    found = []
    for ws in all_ws:
        name = ws.get("name", "").strip()
        if name in target_names:
            found.append((name, ws["id"]))

    if not found:
        logger.info("None of the specified workspaces were found")
        return

    logger.info(f"Found {len(found)} matching workspaces:")
    for name, wid in sorted(found):
        logger.info(f"  • {name} ({wid})")

    successes = 0
    for name, ws_id in found:
        if delete_workspace(token, ws_id, name):
            successes += 1

    logger.info(f"Deletion completed. Successfully deleted {successes}/{len(found)} workspaces.")


if __name__ == "__main__":
    main()