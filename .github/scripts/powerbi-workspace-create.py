# create_fabric_workspaces.py
"""
Creates Power BI / Microsoft Fabric workspaces with environment suffixes
and assigns admin members.

Supports selective environment creation via environment variables:
CREATE_DEV, CREATE_UAT, CREATE_PRD (true/false strings from GitHub Actions)

Requirements:
- Python 3.8+
- pip install python-dotenv requests
"""

import os
import requests
from dotenv import load_dotenv
import logging
from typing import List

# -------------------------------
# CONFIGURATION & LOGGING
# -------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ──── Read from environment variables ────
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

WORKSPACE_NAMES_STR = os.getenv("WORKSPACE_NAMES", "")
ADMIN_EMAILS_STR = os.getenv("ADMIN_EMAILS", "")
FABRIC_CAPACITY_ID = os.getenv("FABRIC_CAPACITY_ID")

# ──── Validate required variables ────
required_vars = {
    "AZURE_TENANT_ID": TENANT_ID,
    "AZURE_CLIENT_ID": CLIENT_ID,
    "AZURE_CLIENT_SECRET": CLIENT_SECRET,
    "WORKSPACE_NAMES": WORKSPACE_NAMES_STR,
}

missing = [k for k, v in required_vars.items() if not v]
if missing:
    logger.error(f"Missing required environment variables: {', '.join(missing)}")
    exit(1)

if not FABRIC_CAPACITY_ID:
    logger.warning("FABRIC_CAPACITY_ID not set → workspaces will be created without assigned capacity")


# -------------------------------
# Microsoft Authentication
# -------------------------------
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


# -------------------------------
# Power BI REST API Helpers
# -------------------------------
def create_workspace(token: str, name: str, capacity_id: str = None) -> dict | None:
    """
    Creates a workspace using the Power BI REST API
    """
    url = "https://api.powerbi.com/v1.0/myorg/groups"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {"name": name}
    if capacity_id:
        body["capacityId"] = capacity_id

    resp = requests.post(url, headers=headers, json=body)

    if resp.status_code in (200, 201):
        logger.info(f"Workspace created: {name}")
        return resp.json()
    else:
        logger.error(f"Failed to create workspace '{name}': {resp.status_code} - {resp.text}")
        return None


def add_workspace_admin(token: str, workspace_id: str, email: str) -> bool:
    """
    Adds a user as Admin to the workspace
    """
    url = f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}/users"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    body = {
        "identifier": email,
        "groupUserAccessRight": "Admin",
        "principalType": "User"
    }

    resp = requests.post(url, headers=headers, json=body)

    if resp.status_code in (200, 201):
        logger.info(f"  → Added admin: {email}")
        return True
    else:
        logger.warning(f"  → Failed to add admin {email}: {resp.status_code} - {resp.text}")
        return False


# -------------------------------
# MAIN LOGIC
# -------------------------------
def main():
    token = get_access_token()

    # Parse base names
    workspace_base_names: List[str] = [
        name.strip() for name in WORKSPACE_NAMES_STR.split(",") if name.strip()
    ]

    admin_emails: List[str] = [
        email.strip() for email in ADMIN_EMAILS_STR.split(",") if email.strip()
    ]

    if not workspace_base_names:
        logger.error("No workspace names provided")
        return

    logger.info(f"Base workspace names: {', '.join(workspace_base_names)}")
    if admin_emails:
        logger.info(f"Admins to assign: {', '.join(admin_emails)}")
    else:
        logger.warning("No admin emails provided → only service principal will be member")

    # ──── Determine which environments to create ────
    create_dev = os.getenv("CREATE_DEV", "false").lower() in ("true", "1", "yes", "on")
    create_uat = os.getenv("CREATE_UAT", "false").lower() in ("true", "1", "yes", "on")
    create_prd = os.getenv("CREATE_PRD", "false").lower() in ("true", "1", "yes", "on")

    selected_envs = []
    if create_dev:
        selected_envs.append(("DEV", "DEV"))
    if create_uat:
        selected_envs.append(("UAT", "UAT"))
    if create_prd:
        selected_envs.append(("PRD", "PRD"))

    if not selected_envs:
        logger.error("No environments selected (DEV/UAT/PRD). Nothing to create.")
        logger.info("Tip: Check at least one environment box in GitHub Actions run dialog.")
        return

    logger.info(f"Selected environments: {', '.join([short for short, _ in selected_envs])}")

    successes = 0

    for base_name in workspace_base_names:
        for env_short, env_display in selected_envs:
            workspace_name = f"{base_name} {env_display}".strip()

            logger.info(f"Creating: {workspace_name}")

            ws = create_workspace(token, workspace_name, FABRIC_CAPACITY_ID)

            if ws and "id" in ws:
                successes += 1
                workspace_id = ws["id"]

                # Add admins if provided
                for email in admin_emails:
                    add_workspace_admin(token, workspace_id, email)

    logger.info(f"Finished. Successfully created {successes} workspaces.")


if __name__ == "__main__":
    main()