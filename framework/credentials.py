"""
Device inventory and credential resolution.

inventory.yml is the source of truth for *which devices exist* and *how to
connect to them* -- vendor, plus connection defaults per vendor with
optional per-host overrides. Passwords are never stored there: only the
name of the environment variable to read them from (see .env.example).

devices.yml (loaded separately, in deploy.py / the GUI) is the source of
truth for *what to configure* -- it doesn't need an entry for every device
in inventory.yml, only the ones that currently have configured intents.
host is the join key between the two files.
"""

import os
from dataclasses import dataclass
from pathlib import Path

import yaml
from dotenv import load_dotenv

INVENTORY_PATH = Path(__file__).resolve().parent / "inventory.yml"
ENV_PATH = Path(__file__).resolve().parent / ".env"


class CredentialsError(Exception):
    """Raised when a device's connection info can't be fully resolved.

    Deliberately loud rather than falling back to a guessed or hardcoded
    default -- a silent wrong guess against a real device is worse than a
    clear failure with an actionable message.
    """


@dataclass
class DeviceConnection:
    host: str
    vendor: str
    username: str
    password: str


def _load_inventory() -> dict:
    if not INVENTORY_PATH.is_file():
        raise CredentialsError(
            f"No inventory file at {INVENTORY_PATH}. Every device must be "
            "declared there before it can be connected to -- see inventory.yml."
        )
    with open(INVENTORY_PATH) as f:
        return yaml.safe_load(f) or {}


def all_hosts() -> list[str]:
    """Every device declared in inventory.yml, in file order."""
    return list(_load_inventory().get("hosts", {}).keys())


def vendor_for_host(host: str) -> str:
    inventory = _load_inventory()
    host_entry = inventory.get("hosts", {}).get(host)
    if host_entry is None:
        raise CredentialsError(f"'{host}' is not declared in inventory.yml")
    vendor = host_entry.get("vendor")
    if not vendor:
        raise CredentialsError(f"'{host}' in inventory.yml has no 'vendor' set")
    return vendor


def resolve_credentials(host: str) -> DeviceConnection:
    """Merge inventory.yml's per-vendor defaults with any per-host override
    for `host`, then resolve the password from the environment.

    Raises CredentialsError, with a specific and actionable message, if:
      - the host isn't declared in inventory.yml at all
      - it has no vendor set
      - there are no connection defaults for that vendor
      - username or password_env can't be resolved
      - the named environment variable isn't actually set

    Never falls back to a hardcoded or guessed credential.
    """
    load_dotenv(ENV_PATH)
    inventory = _load_inventory()

    hosts = inventory.get("hosts", {})
    host_entry = hosts.get(host)
    if host_entry is None:
        raise CredentialsError(f"'{host}' is not declared in inventory.yml")

    vendor = host_entry.get("vendor")
    if not vendor:
        raise CredentialsError(f"'{host}' in inventory.yml has no 'vendor' set")

    vendor_defaults = inventory.get("vendors", {}).get(vendor)
    if vendor_defaults is None:
        raise CredentialsError(
            f"No connection defaults for vendor '{vendor}' in inventory.yml "
            f"(needed for '{host}')"
        )

    def resolve_field(name):
        return host_entry.get(name, vendor_defaults.get(name))

    username = resolve_field("username")
    password_env = resolve_field("password_env")

    if not username:
        raise CredentialsError(
            f"No username configured for '{host}' (vendor '{vendor}') in inventory.yml"
        )
    if not password_env:
        raise CredentialsError(
            f"No password_env configured for '{host}' (vendor '{vendor}') in inventory.yml"
        )

    password = os.getenv(password_env)
    if not password:
        raise CredentialsError(
            f"Environment variable '{password_env}' is not set (needed for '{host}'). "
            f"Copy framework/.env.example to framework/.env and fill it in."
        )

    return DeviceConnection(host=host, vendor=vendor, username=username, password=password)
