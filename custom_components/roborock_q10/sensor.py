"""Sensor platform for Roborock Q10 integration."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import RoborockQ10ConfigEntry, RoborockQ10Coordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RoborockQ10ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities([
        RoborockBatterySensor(coordinator),
        RoborockMainBrushSensor(coordinator),
        RoborockSideBrushSensor(coordinator),
        RoborockFilterSensor(coordinator),
        RoborockSensorLifeSensor(coordinator),
    ])


class RoborockBaseSensor(SensorEntity):
    """Base class for Roborock sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RoborockQ10Coordinator) -> None:
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._attr_device_info = coordinator.device_info

    async def async_added_to_hass(self) -> None:
        """Register for updates."""
        await super().async_added_to_hass()
        self._coordinator.register_update_callback(self._handle_update)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister for updates."""
        self._coordinator.unregister_update_callback(self._handle_update)
        await super().async_will_remove_from_hass()

    @callback
    def _handle_update(self) -> None:
        """Handle state update."""
        self.async_write_ha_state()


class RoborockBatterySensor(RoborockBaseSensor):
    """Battery level sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_translation_key = "battery"

    def __init__(self, coordinator: RoborockQ10Coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_battery"

    @property
    def native_value(self) -> int | None:
        """Return the battery level."""
        return self._coordinator.state.battery


class RoborockMainBrushSensor(RoborockBaseSensor):
    """Main brush life remaining sensor."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:brush"
    _attr_translation_key = "main_brush_life"

    def __init__(self, coordinator: RoborockQ10Coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_main_brush"

    @property
    def native_value(self) -> int | None:
        """Return the main brush life remaining."""
        return self._coordinator.state.main_brush_life


class RoborockSideBrushSensor(RoborockBaseSensor):
    """Side brush life remaining sensor."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:brush"
    _attr_translation_key = "side_brush_life"

    def __init__(self, coordinator: RoborockQ10Coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_side_brush"

    @property
    def native_value(self) -> int | None:
        """Return the side brush life remaining."""
        return self._coordinator.state.side_brush_life


class RoborockFilterSensor(RoborockBaseSensor):
    """Filter life remaining sensor."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:air-filter"
    _attr_translation_key = "filter_life"

    def __init__(self, coordinator: RoborockQ10Coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_filter"

    @property
    def native_value(self) -> int | None:
        """Return the filter life remaining."""
        return self._coordinator.state.filter_life


class RoborockSensorLifeSensor(RoborockBaseSensor):
    """Sensor (cliff/wall) life remaining sensor."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:signal-distance-variant"
    _attr_translation_key = "sensor_life"

    def __init__(self, coordinator: RoborockQ10Coordinator) -> None:
        """Initialize."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_sensor"

    @property
    def native_value(self) -> int | None:
        """Return the sensor life remaining."""
        return self._coordinator.state.sensor_life
