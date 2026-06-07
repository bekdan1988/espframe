#!/usr/bin/env python3
"""Shared Espframe product metadata loader.

The product JSON is intentionally small and dependency-free so release scripts,
local checks, and CI workflows can all read the same device and setting data.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
PRODUCT_PATH = ROOT / "product" / "espframe.json"
WEB_STATIC_ENTITIES = {
    "firmware": {"entity": "text_sensor/Firmware: Version", "fetch": True},
    "timezone": {
        "entity": "select/Clock: Timezone",
        "optionsKey": "tz_options",
        "default": "Europe/London (GMT+0)",
        "fetch": True,
    },
    "ntp_server_1": {"entity": "text/Clock: NTP Server 1", "default": "0.pool.ntp.org", "fetch": True},
    "ntp_server_2": {"entity": "text/Clock: NTP Server 2", "default": "1.pool.ntp.org", "fetch": True},
    "ntp_server_3": {"entity": "text/Clock: NTP Server 3", "default": "2.pool.ntp.org", "fetch": True},
    "album_ids": {"entity": "text/Photos: Album IDs", "fetch": True},
    "album_labels": {"entity": "text/Photos: Album Labels", "fetch": True},
    "person_ids": {"entity": "text/Photos: Person IDs", "fetch": True},
    "person_labels": {"entity": "text/Photos: Person Labels", "fetch": True},
    "sunrise": {"entity": "text_sensor/Screen: Sunrise", "fetch": True},
    "sunset": {"entity": "text_sensor/Screen: Sunset", "fetch": True},
    "developer_features_enabled": {"entity": "switch/Developer: Features", "boolFromState": True, "fetch": True},
    "show_clock": {"entity": "switch/Clock: Show", "boolFromState": True, "default": True},
}
WEB_ENTITY_ALIASES = {
    "schedule_enabled": [{"entity": "switch/Screen: Schedule", "boolFromState": True}],
    "schedule_on_hour": [{"entity": "number/Screen: Schedule On", "default": 6, "number": True}],
    "schedule_off_hour": [{"entity": "number/Screen: Schedule Off", "default": 23, "number": True}],
}
WEB_MANUAL_ENTITIES = {
    "immich_url": {"entity": "text/Connection: Server URL", "firmware_file": "common/addon/immich_config.yaml"},
    "api_key": {"entity": "text/Connection: API Key", "firmware_file": "common/addon/immich_config.yaml"},
    "backlight": {"entity": "light/Screen: Backlight", "firmware_file": "common/addon/backlight.yaml"},
    "update": {"entity": "update/Firmware: Update", "firmware_file": "common/addon/firmware_update.yaml"},
    "update_beta": {"entity": "update/Firmware: Update Beta", "firmware_file": "common/addon/firmware_update.yaml"},
    "apply_photo_source": {"entity": "button/Apply Photo Source", "firmware_file": "common/addon/immich_filter.yaml"},
    "firmware_check": {"entity": "button/Firmware: Check for Update", "firmware_file": "common/addon/firmware_update.yaml"},
}
WEB_LOCAL_STATE_KEYS = {
    "api_key",
    "backlight_on",
    "beta_available",
    "beta_version",
    "brightness",
    "brightness_current",
    "immich_url",
    "installed_version",
    "latest_version",
    "tz_labels",
    "tz_options",
    "update_available",
}
DOCS_SETTINGS_TABLES = {
    ROOT / "docs" / "screen-settings.md": {
        "screen_brightness": {"settings": ["brightness_day", "brightness_night"]},
        "night_schedule": {
            "settings": [
                "schedule_enabled",
                "schedule_on_hour",
                "schedule_off_hour",
                "schedule_wake_timeout",
            ]
        },
        "screen_rotation": {"settings": ["screen_rotation"]},
    },
    ROOT / "docs" / "screen-tone.md": {
        "screen_tone": {"settings": ["base_tone_enabled", "base_tone"]},
        "night_tone": {"settings": ["warm_tones_enabled", "warm_tone_intensity"]},
        "warm_tone_override": {"settings": ["warm_tone_override"]},
    },
    ROOT / "docs" / "photo-sources.md": {
        "source": {
            "columns": ["Setting", "Default", "Format", "Description"],
            "settings": ["photo_source"],
        },
        "date_filtering": {
            "columns": ["Setting", "Default", "Format", "Description"],
            "settings": [
                "date_filter_enabled",
                "date_filter_mode",
                "date_from",
                "date_to",
                "relative_amount",
                "relative_unit",
            ],
        },
        "layout": {
            "settings": ["portrait_pairing", "photo_orientation", "display_mode"],
        },
        "metadata": {
            "settings": [
                "photo_metadata_location_enabled",
                "photo_metadata_date_enabled",
                "photo_metadata_date_format",
                "photo_metadata_date_taken_format",
            ],
        },
        "frequency": {
            "settings": ["interval", "conn_timeout"],
        },
    },
    ROOT / "docs" / "firmware-update.md": {
        "firmware_controls": {
            "columns": ["Control", "Type", "Default", "Description"],
            "settings": [
                "auto_update",
                "beta_channel",
                "update_frequency",
                "firmware_manifest_url",
                "firmware_beta_manifest_url",
            ],
        },
    },
}
DOCS_SETTINGS_TABLE_COLUMNS = {"Control", "Default", "Description", "Format", "Setting", "Type"}


def load_product(path: Path = PRODUCT_PATH) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise RuntimeError(f"Product metadata not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Product metadata is not valid JSON: {exc}") from exc

    if not isinstance(data.get("project"), dict):
        raise RuntimeError("Product metadata must contain a project object")
    if not isinstance(data.get("devices"), list) or not data["devices"]:
        raise RuntimeError("Product metadata must contain at least one device")
    if not isinstance(data.get("settings"), list):
        raise RuntimeError("Product metadata must contain a settings list")
    return data


def project_value(key: str, default: str = "") -> str:
    value = load_product()["project"].get(key, default)
    return str(value)


def devices_by_slug() -> dict[str, dict[str, Any]]:
    devices = {}
    for device in load_product()["devices"]:
        slug = str(device.get("slug", "")).strip()
        if not slug:
            raise RuntimeError("Every product device needs a slug")
        if slug in devices:
            raise RuntimeError(f"Duplicate product device slug: {slug}")
        devices[slug] = device
    return devices


def public_base_url(product: dict[str, Any] | None = None) -> str:
    data = product if product is not None else load_product()
    return str(data["project"].get("public_base_url", "")).rstrip("/")


def device_public_manifest_urls(product: dict[str, Any] | None = None) -> dict[str, dict[str, str]]:
    data = product if product is not None else load_product()
    base_url = public_base_url(data)
    return {
        str(device["slug"]): {
            "stable": f'{base_url}/{str(device["public_manifest"]).lstrip("/")}',
            "beta": f'{base_url}/{str(device["public_beta_manifest"]).lstrip("/")}',
        }
        for device in data["devices"]
    }


def default_public_manifest_urls(product: dict[str, Any] | None = None) -> dict[str, str]:
    data = product if product is not None else load_product()
    first_device = data["devices"][0]
    return device_public_manifest_urls(data)[str(first_device["slug"])]


def build_yaml_stem(build_yaml: str) -> str:
    name = Path(build_yaml).name
    if name.endswith(".factory.yaml"):
        return name[: -len(".factory.yaml")]
    if name.endswith(".yaml"):
        return name[: -len(".yaml")]
    return name


def build_yaml_device_name(build_yaml: str) -> str:
    path = ROOT / build_yaml
    text = path.read_text()
    match = re.search(r'(?m)^  name: "([^"]+)"$', text)
    if not match:
        raise RuntimeError(f"{path.relative_to(ROOT)} is missing substitutions.name")
    return match.group(1)


def release_matrix_devices(product: dict[str, Any] | None = None) -> list[dict[str, str]]:
    data = product if product is not None else load_product()
    result: list[dict[str, str]] = []
    for device in data["devices"]:
        build_yaml = str(device["build_yaml"])
        result.append(
            {
                "slug": str(device["slug"]),
                "yaml": build_yaml_stem(build_yaml),
                "build_name": build_yaml_device_name(build_yaml),
                "chip": str(device["chip"]),
            }
        )
    return result


def settings() -> list[dict[str, Any]]:
    return list(load_product()["settings"])


def web_settings_metadata(product_settings: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for setting in product_settings if product_settings is not None else settings():
        entity = setting["entity"]
        key = str(setting["key"])
        result[key] = {
            "entity": f'{entity["domain"]}/{entity["name"]}',
            "domain": entity["domain"],
            "default": setting.get("default", ""),
            "options": setting.get("options", []),
        }
        if setting.get("developer_options"):
            result[key]["developerOptions"] = setting["developer_options"]
        for field in ("min", "max", "step"):
            if field in setting:
                result[key][field] = setting[field]
    return result


def web_static_entities_metadata() -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for key, metadata in WEB_STATIC_ENTITIES.items():
        result[key] = {field: value for field, value in metadata.items() if field != "fetch"}
    return result


def web_entity_aliases_metadata() -> dict[str, list[dict[str, Any]]]:
    return {key: [dict(alias) for alias in aliases] for key, aliases in WEB_ENTITY_ALIASES.items()}


def web_manual_entities_metadata() -> dict[str, dict[str, Any]]:
    return {key: {"entity": metadata["entity"]} for key, metadata in WEB_MANUAL_ENTITIES.items()}


def web_initial_fetch_keys(product_settings: list[dict[str, Any]] | None = None) -> list[str]:
    keys: list[str] = []

    def add(key: str) -> None:
        if key not in keys:
            keys.append(key)

    add("firmware")
    for setting in product_settings if product_settings is not None else settings():
        add(str(setting["key"]))
    for key, metadata in WEB_STATIC_ENTITIES.items():
        if metadata.get("fetch"):
            add(key)
    return keys
