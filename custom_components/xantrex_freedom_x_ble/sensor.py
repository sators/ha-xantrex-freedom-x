"""Conservative telemetry sensors and opt-in provisional interpretations."""

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_PROVISIONAL
from .entity import XantrexEntity


@dataclass(frozen=True, kw_only=True)
class XantrexSensorDescription(SensorEntityDescription):
    provisional: bool = False


SENSORS = (
    XantrexSensorDescription(
        key="ac_voltage",
        name="AC voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    XantrexSensorDescription(
        key="ac_frequency",
        name="AC frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    XantrexSensorDescription(
        key="battery_voltage",
        name="Battery voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    XantrexSensorDescription(
        key="ac_voltage_2",
        name="AC voltage channel 2",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    XantrexSensorDescription(
        key="ac_frequency_2",
        name="AC frequency channel 2",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
    ),
    XantrexSensorDescription(
        key="ac_current_provisional",
        name="AC current (provisional)",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        provisional=True,
    ),
    XantrexSensorDescription(
        key="ac_power_provisional",
        name="AC power (provisional)",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        provisional=True,
    ),
    XantrexSensorDescription(
        key="load_provisional",
        name="Load (provisional)",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        provisional=True,
    ),
    XantrexSensorDescription(
        key="battery_level_provisional",
        name="Reported battery level (provisional)",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        provisional=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        XantrexSensor(coordinator, description)
        for description in SENSORS
        if not description.provisional or entry.data.get(CONF_PROVISIONAL, False)
    )


class XantrexSensor(XantrexEntity, SensorEntity):
    entity_description: XantrexSensorDescription

    def __init__(self, coordinator, description: XantrexSensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.data.identity.serial}_{description.key}"

    @property
    def native_value(self):
        return self.coordinator.data.telemetry.values[self.entity_description.key]
