"""Conservative telemetry sensors and opt-in provisional interpretations."""

from dataclasses import dataclass, replace

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
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTime,
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
        key="ac_input_current",
        suggested_display_precision=1,
        name="AC input current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
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
        entity_registry_enabled_default=False,
    ),
) + tuple(
    XantrexSensorDescription(
        key=key,
        name=name,
        native_unit_of_measurement=unit,
        suggested_display_precision=precision,
        device_class=device_class,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        icon="mdi:eye-settings-outline",
    )
    for key, name, unit, precision, device_class in (
        (
            "low_battery_cutoff",
            "Configured low battery cutoff",
            UnitOfElectricPotential.VOLT,
            1,
            SensorDeviceClass.VOLTAGE,
        ),
        (
            "low_battery_cutoff_delay",
            "Configured low battery cutoff delay",
            UnitOfTime.SECONDS,
            0,
            SensorDeviceClass.DURATION,
        ),
        (
            "low_battery_recovery",
            "Configured low battery recovery",
            UnitOfElectricPotential.VOLT,
            1,
            SensorDeviceClass.VOLTAGE,
        ),
        (
            "power_save_time",
            "Configured power save time",
            UnitOfTime.HOURS,
            0,
            SensorDeviceClass.DURATION,
        ),
        (
            "configured_output_frequency",
            "Configured output frequency",
            UnitOfFrequency.HERTZ,
            1,
            SensorDeviceClass.FREQUENCY,
        ),
        (
            "configured_output_voltage",
            "Configured output voltage",
            UnitOfElectricPotential.VOLT,
            0,
            SensorDeviceClass.VOLTAGE,
        ),
        (
            "output_power_limit",
            "Configured output power limit",
            UnitOfPower.WATT,
            0,
            SensorDeviceClass.POWER,
        ),
        (
            "output_power_limit_delay",
            "Configured output power limit delay",
            UnitOfTime.SECONDS,
            0,
            SensorDeviceClass.DURATION,
        ),
        (
            "utility_ac_under_voltage",
            "Configured utility AC under voltage",
            UnitOfElectricPotential.VOLT,
            0,
            SensorDeviceClass.VOLTAGE,
        ),
    )
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        XantrexSensor(
            coordinator,
            replace(description, entity_registry_enabled_default=True)
            if description.provisional and entry.data.get(CONF_PROVISIONAL, False)
            else description,
        )
        for description in SENSORS
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
