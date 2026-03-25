"""Coordinator for Roborock Q10 integration."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeAlias

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.device_registry import DeviceInfo

from roborock import RRiot, Reference, UserData
from roborock.data.b01_q10.b01_q10_containers import Q10Status
from roborock.data.b01_q10.b01_q10_code_mappings import (
    YXDeviceState,
    YXFanLevel,
    YXWaterLevel,
)
from roborock.devices.device_manager import (
    DeviceManager,
    UserParams,
    create_device_manager,
)
from roborock.devices.traits.b01.q10 import Q10PropertiesApi
from roborock.exceptions import (
    RoborockException,
    RoborockInvalidCredentials,
    RoborockInvalidUserAgreement,
    RoborockNoUserAgreement,
)

from .const import CONF_USER_DATA, DOMAIN

_LOGGER = logging.getLogger(__name__)

RoborockQ10ConfigEntry: TypeAlias = ConfigEntry


@dataclass
class DeviceState:
    """Current state of the vacuum."""

    battery: int | None = None
    status: YXDeviceState | None = None
    fan_level: YXFanLevel | None = None
    water_level: YXWaterLevel | None = None
    clean_mode: str | None = None
    clean_area: int | None = None
    clean_time: int | None = None
    cleaning_progress: int | None = None
    fault: int | None = None
    main_brush_life: int | None = None
    side_brush_life: int | None = None
    filter_life: int | None = None
    sensor_life: int | None = None


def _build_user_data(data: dict[str, Any]) -> UserData:
    """Build UserData from stored config entry data."""
    ud = data[CONF_USER_DATA]
    ref = Reference(
        r=ud["rriot"]["r"]["r"],
        a=ud["rriot"]["r"]["a"],
        m=ud["rriot"]["r"]["m"],
        l=ud["rriot"]["r"]["l"],
    )
    rriot = RRiot(
        u=ud["rriot"]["u"],
        s=ud["rriot"]["s"],
        h=ud["rriot"]["h"],
        k=ud["rriot"]["k"],
        r=ref,
    )
    return UserData(
        rriot=rriot,
        uid=None,
        tokentype=None,
        token=ud["token"],
        rruid=ud["rruid"],
        region=ud.get("region"),
        countrycode=ud.get("country_code"),
        nickname=None,
        tuya_device_state=None,
        avatarurl=None,
    )


class RoborockQ10Coordinator:
    """Manages the connection to the Roborock Q10 device."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry
        self._manager: DeviceManager | None = None
        self._q10: Q10PropertiesApi | None = None
        self._device_name: str = "Roborock Q10"
        self._device_id: str = ""
        self._model: str = "roborock.vacuum.ss07"
        self._fw_version: str = ""
        self._state = DeviceState()
        self._update_callbacks: list[Callable[[], None]] = []
        self._status_listener_unsub: Callable[[], None] | None = None
        self._closed: bool = False

    @property
    def state(self) -> DeviceState:
        """Return the current device state."""
        return self._state

    @property
    def q10(self) -> Q10PropertiesApi | None:
        """Return the Q10 properties API."""
        return self._q10

    @property
    def device_id(self) -> str:
        """Return the device unique ID."""
        return self._device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the device registry."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device_name,
            manufacturer="Roborock",
            model=self._model,
            sw_version=self._fw_version,
        )

    def register_update_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback for state updates."""
        self._update_callbacks.append(callback)

    def unregister_update_callback(self, callback: Callable[[], None]) -> None:
        """Unregister a callback."""
        self._update_callbacks.remove(callback)

    def _notify_update(self) -> None:
        """Notify all registered callbacks of a state update."""
        for cb in self._update_callbacks:
            cb()

    async def async_setup(self) -> None:
        """Set up the connection to the device."""
        user_data = _build_user_data(self.entry.data)
        email = self.entry.data[CONF_EMAIL]

        params = UserParams(user_data=user_data, username=email)

        try:
            self._manager = await asyncio.wait_for(
                create_device_manager(params, prefer_cache=False),
                timeout=30,
            )
        except asyncio.TimeoutError as err:
            raise ConfigEntryNotReady("Timeout connecting to Roborock cloud") from err
        except (
            RoborockInvalidCredentials,
            RoborockInvalidUserAgreement,
            RoborockNoUserAgreement,
        ) as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except RoborockException as err:
            raise ConfigEntryNotReady(str(err)) from err

        # Find Q10 device.
        # NOTE: _devices is a private attribute of DeviceManager. If python-roborock
        # exposes a public device-enumeration API in a future release, prefer that.
        for duid, dev in self._manager._devices.items():
            q10 = dev.b01_q10_properties
            if q10 is not None:
                self._q10 = q10
                self._device_id = duid
                self._device_name = dev.name
                self._model = dev.product.model
                self._fw_version = dev.device_info.fv or ""

                # Subscribe to status updates
                self._status_listener_unsub = q10.status.add_update_listener(
                    self._on_status_update
                )

                # Request initial data
                try:
                    await asyncio.wait_for(q10.refresh(), timeout=10)
                    await asyncio.sleep(3)  # Wait for MQTT push
                    self._sync_status(q10.status)
                except (asyncio.TimeoutError, RoborockException):
                    _LOGGER.warning("Could not get initial status, will update on next push")

                _LOGGER.info(
                    "Connected to %s (duid=%s, fw=%s)",
                    self._device_name,
                    self._device_id,
                    self._fw_version,
                )
                return

        raise ConfigEntryNotReady("No Q10 device found in account")

    def _on_status_update(self) -> None:
        """Handle status update from the device.

        python-roborock dispatches this callback on the asyncio event loop, so
        calling _sync_status and _notify_update directly is safe.  We still use
        call_soon_threadsafe as a defensive measure in case the callback ever
        fires from a background thread, and to consolidate both the state-sync
        and the HA entity notification into a single scheduled call so that
        entities never see a partially-updated DeviceState.
        """
        if self._q10:
            status = self._q10.status
            self.hass.loop.call_soon_threadsafe(self._apply_status_update, status)

    def _apply_status_update(self, status: Q10Status) -> None:
        """Sync state and notify entities — always runs on the HA event loop."""
        self._sync_status(status)
        self._notify_update()

    def _sync_status(self, status: Q10Status) -> None:
        """Sync Q10Status fields to our DeviceState."""
        self._state.battery = status.battery
        self._state.status = status.status
        self._state.fan_level = status.fan_level
        self._state.water_level = status.water_level
        self._state.clean_mode = status.clean_mode.value if status.clean_mode else None
        self._state.clean_area = status.clean_area
        self._state.clean_time = status.clean_time
        self._state.cleaning_progress = status.cleaning_progress
        self._state.fault = status.fault
        self._state.main_brush_life = status.main_brush_life
        self._state.side_brush_life = status.side_brush_life
        self._state.filter_life = status.filter_life
        self._state.sensor_life = status.sensor_life

    async def async_close(self) -> None:
        """Close the connection.

        Idempotent — safe to call from both async_unload_entry and the
        homeassistant_stop shutdown listener registered in __init__.py.
        """
        if self._closed:
            return
        self._closed = True

        if self._status_listener_unsub is not None:
            self._status_listener_unsub()
            self._status_listener_unsub = None

        if self._manager is not None:
            manager = self._manager
            self._manager = None
            try:
                await asyncio.wait_for(manager.close(), timeout=5)
            except Exception:
                _LOGGER.debug("Timeout or error closing device manager, forcing shutdown")
