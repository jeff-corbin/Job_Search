"""
vault_client.py
===============
Authenticates to Vault via AppRole and pulls secrets.

Bootstrap vars come from .env:
  VAULT_ADDR      - e.g. http://192.168.68.101:8200
  VAULT_ROLE_ID   - AppRole role ID
  VAULT_SECRET_ID - AppRole secret ID

Secrets live at: kv/data/projects/job-search
"""

import os
import logging
import requests  # type: ignore

log = logging.getLogger(__name__)

_vault_token: str | None = None  # cached for the lifetime of the run


def _get_token() -> str:
    """Authenticate via AppRole, return a Vault token. Cached after first call."""
    global _vault_token
    if _vault_token:
        return _vault_token

    addr    = os.getenv("VAULT_ADDR", "").rstrip("/")
    role_id = os.getenv("VAULT_ROLE_ID", "")
    secret_id = os.getenv("VAULT_SECRET_ID", "")

    if not all([addr, role_id, secret_id]):
        raise EnvironmentError("VAULT_ADDR, VAULT_ROLE_ID, and VAULT_SECRET_ID must be set in .env")

    resp = requests.post(
        f"{addr}/v1/auth/approle/login",
        json={"role_id": role_id, "secret_id": secret_id},
        timeout=10,
    )
    resp.raise_for_status()
    _vault_token = resp.json()["auth"]["client_token"]
    log.info("Vault: authenticated via AppRole")
    return _vault_token


def get_secrets() -> dict:
    """
    Pull all secrets from kv/projects/job-search.
    Returns a flat dict of key → value.
    """
    addr  = os.getenv("VAULT_ADDR", "").rstrip("/")
    token = _get_token()

    resp = requests.get(
        f"{addr}/v1/kv/data/projects/job-search",
        headers={"X-Vault-Token": token},
        timeout=10,
    )
    resp.raise_for_status()
    secrets = resp.json()["data"]["data"]
    log.info(f"Vault: pulled {len(secrets)} secret(s)")
    return secrets