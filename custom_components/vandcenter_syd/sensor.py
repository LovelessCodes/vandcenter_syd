"""Sensor platform for VandCenter Syd."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Set up sensors."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    entities = []
    devices = coordinator.data.get("devices")

    if not devices:
        return

    for device_id, data in devices.items():
        device = data["device"]
        location = data["location"]
        loc_id = location["LocationId"]

        daily_sensor = VandCenterDailySensor(coordinator, device_id, device, loc_id)
        total_sensor = VandCenterTotalSensor(coordinator, device_id, device, loc_id)
        stats_sensor = VandCenterStatsSensor(coordinator, device_id, device, loc_id)
        highest_sensor = VandCenterHighestSensor(coordinator, device_id, device, loc_id)

        entities.append(total_sensor)
        entities.append(daily_sensor)
        entities.append(stats_sensor)
        entities.append(highest_sensor)

    entities.append(VandCenterPriceSensor(coordinator))

    async_add_entities(entities)


class VandCenterDailySensor(CoordinatorEntity, SensorEntity):
    """Sensor for yesterday's water usage (last complete day)."""

    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator, device_id, device_info, loc_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device_id = device_id
        self.loc_id = loc_id
        self._attr_unique_id = f"{device_id}_daily_usage"
        self._attr_name = f"{device_info['BrandName']} Daily Usage"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_info["BrandName"],
            manufacturer="Axioma",
            model=device_info["DeviceType"],
        )

    @property
    def native_value(self):
        """Return yesterday's usage (most recent complete day)."""
        devices = self.coordinator.data.get("devices")
        if not devices:
            return None
        data = devices.get(self.device_id, {})
        buckets = data.get("usage", {}).get("Buckets", [])

        if not buckets:
            return None

        # Last bucket might be incomplete (today in progress),
        # so return second-to-last if available
        if len(buckets) >= 2:
            return round(buckets[-2]["Value"], 3)
        return round(buckets[-1]["Value"], 3)


class VandCenterHighestSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_device_class = SensorDeviceClass.WATER

    def __init__(self, coordinator, device_id, device_info, loc_id):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.device_id = device_id
        self.loc_id = loc_id
        self._attr_unique_id = f"{device_id}_highest_usage"
        self._attr_name = f"{device_info['BrandName']} Highest Usage (past 14 days)"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_info["BrandName"],
            manufacturer="Axioma",
            model=device_info["DeviceType"],
        )

    @property
    def native_value(self):
        """Return cumulative usage (sum of all daily values)."""
        devices = self.coordinator.data.get("devices")
        if devices is None:
            return None
        data = devices.get(self.device_id, {})
        return data.get("usage", {}).get("HighestUsageInPeriod")


class VandCenterTotalSensor(CoordinatorEntity, SensorEntity):
    """Sensor for total cumulative water meter reading."""

    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator, device_id, device_info, loc_id):
        super().__init__(coordinator)
        self.device_id = device_id
        self.loc_id = loc_id
        self._attr_unique_id = f"{device_id}_total_reading"
        self._attr_name = f"{device_info['BrandName']} Total"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_info["BrandName"],
            manufacturer="Axioma",
            model=device_info["DeviceType"],
        )

    @property
    def native_value(self):
        """Return total cubic meters."""
        devices = self.coordinator.data.get("devices")
        if not devices:
            return None
        data = devices.get(self.device_id, {})
        return data.get("total_reading")

    @property
    def extra_state_attributes(self):
        """Return timestamp of when reading was taken."""
        devices = self.coordinator.data.get("devices")
        if not devices:
            return None
        data = devices.get(self.device_id, {})
        return {"last_reading_timestamp": data.get("reading_timestamp")}


class VandCenterPriceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for price."""

    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_native_unit_of_measurement = "DKK/m³"
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self._attr_unique_id = "vandcentersyd_current_price"
        self._attr_name = "Vandcenter Syd Current Price"

    @property
    def native_value(self):
        """Return the price."""
        return self.coordinator.data.get("price")


class VandCenterStatsSensor(CoordinatorEntity, SensorEntity):
    """Sensor for average daily consumption."""

    _attr_device_class = SensorDeviceClass.WATER
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_state_class = SensorStateClass.TOTAL

    def __init__(self, coordinator, device_id, device_info, loc_id):
        super().__init__(coordinator)
        self.device_id = device_id
        self.loc_id = loc_id
        self._attr_unique_id = f"{device_id}_avg_daily"
        self._attr_name = f"{device_info['BrandName']} Avg Daily"

    @property
    def native_value(self):
        devices = self.coordinator.data.get("devices")
        if not devices:
            return None
        data = devices.get(self.device_id, {})
        return data.get("usage", {}).get("AverageDailyUsage")
