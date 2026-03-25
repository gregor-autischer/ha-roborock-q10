"""Roborock Q10 integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import RoborockQ10ConfigEntry, RoborockQ10Coordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: RoborockQ10ConfigEntry
) -> bool:
    """Set up Roborock Q10 from a config entry."""
    coordinator = RoborockQ10Coordinator(hass, entry)
    await coordinator.async_setup()

    entry.runtime_data = coordinator

    async def _shutdown(event=None) -> None:
        await coordinator.async_close()

    entry.async_on_unload(
        hass.bus.async_listen_once("homeassistant_stop", _shutdown)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: RoborockQ10ConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_close()
    return unload_ok
