"""Vacuum platform for Roborock Q10 integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from roborock import B01_Q10_DP
from roborock.data.b01_q10.b01_q10_code_mappings import YXDeviceState, YXFanLevel

from .const import DOMAIN
from .coordinator import RoborockQ10ConfigEntry, RoborockQ10Coordinator

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0

# Map Roborock fan levels to HA fan speed strings
FAN_SPEED_MAP: dict[YXFanLevel, str] = {
    YXFanLevel.QUIET: "quiet",
    YXFanLevel.BALANCED: "balanced",
    YXFanLevel.TURBO: "turbo",
    YXFanLevel.MAX: "max",
    YXFanLevel.MAX_PLUS: "max_plus",
}

FAN_SPEED_REVERSE: dict[str, YXFanLevel] = {v: k for k, v in FAN_SPEED_MAP.items()}

# Map Roborock device states to HA vacuum activities
STATE_MAP: dict[YXDeviceState, VacuumActivity] = {
    YXDeviceState.SLEEPING: VacuumActivity.DOCKED,
    YXDeviceState.IDLE: VacuumActivity.IDLE,
    YXDeviceState.CLEANING: VacuumActivity.CLEANING,
    YXDeviceState.RETURNING_HOME: VacuumActivity.RETURNING,
    YXDeviceState.CHARGING: VacuumActivity.DOCKED,
    YXDeviceState.PAUSED: VacuumActivity.PAUSED,
    YXDeviceState.ERROR: VacuumActivity.ERROR,
    YXDeviceState.SWEEPING: VacuumActivity.CLEANING,
    YXDeviceState.MOPPING: VacuumActivity.CLEANING,
    YXDeviceState.SWEEP_AND_MOP: VacuumActivity.CLEANING,
    YXDeviceState.EMPTYING_THE_BIN: VacuumActivity.DOCKED,
    YXDeviceState.MAPPING: VacuumActivity.CLEANING,
    YXDeviceState.UPDATING: VacuumActivity.IDLE,
    YXDeviceState.RELOCATING: VacuumActivity.IDLE,
    YXDeviceState.SAVING_MAP: VacuumActivity.IDLE,
    YXDeviceState.TRANSITIONING: VacuumActivity.CLEANING,
    YXDeviceState.WAITING_TO_CHARGE: VacuumActivity.DOCKED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RoborockQ10ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the vacuum from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([RoborockQ10Vacuum(coordinator)])


class RoborockQ10Vacuum(StateVacuumEntity):
    """Representation of the Roborock Q10 vacuum."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = (
        VacuumEntityFeature.STATE
        | VacuumEntityFeature.START
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.LOCATE
        | VacuumEntityFeature.SEND_COMMAND
    )
    _attr_fan_speed_list = list(FAN_SPEED_REVERSE.keys())
    _attr_translation_key = "roborock_q10"

    def __init__(self, coordinator: RoborockQ10Coordinator) -> None:
        """Initialize the vacuum entity."""
        self._coordinator = coordinator
        self._attr_unique_id = coordinator.device_id
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self) -> None:
        """Register for state updates when added to hass."""
        self._coordinator.register_update_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister for state updates when removed."""
        self._coordinator.unregister_update_callback(self._handle_update)

    @callback
    def _handle_update(self) -> None:
        """Handle state update from coordinator."""
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        """Return True if the vacuum is available."""
        return self._coordinator.q10 is not None

    @property
    def activity(self) -> VacuumActivity | None:
        """Return the current vacuum activity."""
        status = self._coordinator.state.status
        if status is None:
            return None
        return STATE_MAP.get(status, VacuumActivity.IDLE)

    @property
    def battery_level(self) -> int | None:
        """Return the battery level."""
        return self._coordinator.state.battery

    @property
    def fan_speed(self) -> str | None:
        """Return the current fan speed."""
        level = self._coordinator.state.fan_level
        if level is None:
            return None
        return FAN_SPEED_MAP.get(level, level.value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        state = self._coordinator.state
        attrs = {}
        if state.clean_area is not None:
            attrs["clean_area"] = state.clean_area
        if state.clean_time is not None:
            attrs["clean_time"] = state.clean_time
        if state.cleaning_progress is not None:
            attrs["cleaning_progress"] = state.cleaning_progress
        if state.water_level is not None:
            attrs["water_level"] = state.water_level.value if hasattr(state.water_level, 'value') else state.water_level
        if state.clean_mode is not None:
            attrs["clean_mode"] = state.clean_mode
        if state.fault is not None and state.fault != 0:
            attrs["fault"] = state.fault
        if state.main_brush_life is not None:
            attrs["main_brush_life"] = state.main_brush_life
        if state.side_brush_life is not None:
            attrs["side_brush_life"] = state.side_brush_life
        if state.filter_life is not None:
            attrs["filter_life"] = state.filter_life
        return attrs

    async def async_start(self) -> None:
        """Start cleaning."""
        q10 = self._coordinator.q10
        if q10:
            await q10.vacuum.start_clean()

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop cleaning."""
        q10 = self._coordinator.q10
        if q10:
            await q10.vacuum.stop_clean()

    async def async_pause(self) -> None:
        """Pause cleaning."""
        q10 = self._coordinator.q10
        if q10:
            await q10.vacuum.pause_clean()

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Stop cleaning and return to dock."""
        q10 = self._coordinator.q10
        if q10:
            await q10.vacuum.stop_clean()
            await asyncio.sleep(1)
            await q10.vacuum.return_to_dock()

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set the fan speed."""
        q10 = self._coordinator.q10
        level = FAN_SPEED_REVERSE.get(fan_speed)
        if q10 and level:
            await q10.vacuum.set_fan_level(level)

    async def async_locate(self, **kwargs: Any) -> None:
        """Locate the vacuum (make it beep)."""
        q10 = self._coordinator.q10
        if q10:
            await q10.command.send(B01_Q10_DP.SEEK, params={})

    async def async_send_command(
        self,
        command: str,
        params: dict[str, Any] | list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Send a raw command to the vacuum."""
        q10 = self._coordinator.q10
        if not q10:
            return

        dp = getattr(B01_Q10_DP, command.upper(), None)
        if dp is None:
            _LOGGER.error("Unknown command: %s", command)
            return

        await q10.command.send(dp, params=params or {})
