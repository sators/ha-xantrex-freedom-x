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
    UnitOfApparentPower,
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
        key="power_path",
        translation_key="power_path",
        device_class=SensorDeviceClass.ENUM,
        options=["ac_bypass", "dc_inverting", "no_ac_output"],
        icon="mdi:transmission-tower",
    ),
    XantrexSensorDescription(
        key="ac_voltage",
        suggested_display_precision=1,
        name="AC input voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    XantrexSensorDescription(
        key="ac_frequency",
        suggested_display_precision=1,
        name="AC input frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    XantrexSensorDescription(
        key="battery_voltage",
        suggested_display_precision=2,
        name="Battery voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    XantrexSensorDescription(
        key="ac_voltage_2",
        suggested_display_precision=1,
        name="AC output voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    XantrexSensorDescription(
        key="ac_frequency_2",
        suggested_display_precision=1,
        name="AC output frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    XantrexSensorDescription(
        key="load_power",
        suggested_display_precision=0,
        name="Load power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    XantrexSensorDescription(
        key="load_percentage",
        suggested_display_precision=0,
        name="Load percentage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    XantrexSensorDescription(
        key="load_apparent_power",
        suggested_display_precision=0,
        name="Load apparent power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
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

    @property
    def extra_state_attributes(self):
        if self.entity_description.key == "power_path":
            return {"basis": "inferred_from_ac_input_output_voltage_and_frequency"}
        return None
