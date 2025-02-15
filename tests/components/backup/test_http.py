"""Tests for the Backup integration."""

import asyncio
from io import StringIO
from unittest.mock import patch

from aiohttp import web
import pytest

from homeassistant.core import HomeAssistant

from .common import TEST_BACKUP, setup_backup_integration

from tests.common import MockUser
from tests.typing import ClientSessionGenerator


async def test_downloading_backup(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
) -> None:
    """Test downloading a backup file."""
    await setup_backup_integration(hass)

    client = await hass_client()

    with (
        patch(
            "homeassistant.components.backup.manager.BackupManager.async_get_backup",
            return_value=TEST_BACKUP,
        ),
        patch("pathlib.Path.exists", return_value=True),
        patch(
            "homeassistant.components.backup.http.FileResponse",
            return_value=web.Response(text=""),
        ),
    ):
        resp = await client.get("/api/backup/download/abc123")
        assert resp.status == 200


async def test_downloading_backup_not_found(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
) -> None:
    """Test downloading a backup file that does not exist."""
    await setup_backup_integration(hass)

    client = await hass_client()

    resp = await client.get("/api/backup/download/abc123")
    assert resp.status == 404


async def test_downloading_as_non_admin(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    hass_admin_user: MockUser,
) -> None:
    """Test downloading a backup file when you are not an admin."""
    hass_admin_user.groups = []
    await setup_backup_integration(hass)

    client = await hass_client()

    resp = await client.get("/api/backup/download/abc123")
    assert resp.status == 401


async def test_uploading_a_backup_file(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
) -> None:
    """Test uploading a backup file."""
    await setup_backup_integration(hass)

    client = await hass_client()

    with patch(
        "homeassistant.components.backup.manager.BackupManager.async_receive_backup",
    ) as async_receive_backup_mock:
        resp = await client.post(
            "/api/backup/upload",
            data={"file": StringIO("test")},
        )
        assert resp.status == 201
        assert async_receive_backup_mock.called


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (OSError("Boom!"), "Can't write backup file Boom!"),
        (asyncio.CancelledError("Boom!"), ""),
    ],
)
async def test_error_handling_uploading_a_backup_file(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    error: Exception,
    message: str,
) -> None:
    """Test error handling when uploading a backup file."""
    await setup_backup_integration(hass)

    client = await hass_client()

    with patch(
        "homeassistant.components.backup.manager.BackupManager.async_receive_backup",
        side_effect=error,
    ):
        resp = await client.post(
            "/api/backup/upload",
            data={"file": StringIO("test")},
        )
        assert resp.status == 500
        assert await resp.text() == message
