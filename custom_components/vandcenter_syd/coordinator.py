"""DataUpdateCoordinator for VandCenter Syd."""

import logging
from datetime import datetime, timedelta, timezone

from aiohttp import ClientResponseError
import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BASE,
    DOMAIN,
    UPDATE_INTERVAL,
    CONF_TOKEN,
    CONF_TOKEN_EXPIRES,
    CONF_EMAIL,
    CONF_PASSWORD,
)

_LOGGER = logging.getLogger(__name__)


class VandCenterCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch data from VandCenter API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.entry = entry
        self.session = async_get_clientsession(hass)

    @property
    def token(self):
        return self.entry.data[CONF_TOKEN]

    async def _async_update_data(self):
        headers = {"Authorization": f"Bearer {self.token}"}

        try:
            return await self._fetch_data(headers)
        except ClientResponseError as err:
            if err.status == 401:
                # Token expired, refresh and retry
                await self._refresh_token()
                headers = {"Authorization": f"Bearer {self.token}"}
                return await self._fetch_data(headers)
            raise UpdateFailed(f"API error: {err}")

    async def _refresh_token(self):
        """Login to get new token."""
        try:
            resp = await self.session.post(
                f"{API_BASE}/Customer/login",
                json={
                    "MatchTag": None,
                    "Email": self.entry.data[CONF_EMAIL],
                    "Password": self.entry.data[CONF_PASSWORD],
                },
            )
            resp.raise_for_status()
            data = await resp.json()

            # Update config entry with new token
            self.hass.config_entries.async_update_entry(
                self.entry,
                data={
                    **self.entry.data,
                    CONF_TOKEN: data["AuthToken"],
                    CONF_TOKEN_EXPIRES: data["ExpiresIn"],
                },
            )
            _LOGGER.debug("Token refreshed successfully")

        except Exception as err:
            _LOGGER.error("Failed to refresh token: %s", err)
            raise UpdateFailed("Authentication failed, please reconfigure integration")

    async def _fetch_data(self, headers) -> dict:
        """Actual data fetching logic."""
        with async_timeout.timeout(30):
            resp = await self.session.get(
                f"{API_BASE}/Customer/details", headers=headers
            )
            resp.raise_for_status()
            customer = await resp.json()

            all_device_data = {}

            for location in customer.get("Locations", []):
                loc_id = location["LocationId"]

                resp = await self.session.get(
                    f"{API_BASE}/Customer/devices",
                    headers=headers,
                    params={
                        "LocationId": loc_id,
                        "IncludeDisabledDevices": "true",
                    },
                )
                resp.raise_for_status()
                devices_resp = await resp.json()

                for device in devices_resp.get("Devices", []):
                    device_id = device["Id"]

                    # Get usage stats (last 14 days)
                    to_date = datetime.now(timezone.utc)
                    from_date = to_date - timedelta(days=14)

                    payload = {
                        "DeviceIds": [device_id],
                        "From": from_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "To": to_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "Interval": "Daily",
                        "QuantityType": "WaterVolume",
                        "Unit": "KubicMeter",
                    }

                    resp = await self.session.post(
                        f"{API_BASE}/Stats/usage/{loc_id}/devices",
                        headers=headers,
                        json=payload,
                    )
                    resp.raise_for_status()
                    usage = await resp.json()

                    total_payload = {
                        "DeviceContainerIds": [device_id],
                        "QuantityTypes": ["WaterVolume"],
                        "Size": 1,
                    }

                    try:
                        resp = await self.session.post(
                            f"{API_BASE}/Stats/readings/devices",
                            headers=headers,
                            json=total_payload,
                        )
                        resp.raise_for_status()
                        readings_data = await resp.json()

                        total_reading = None
                        if readings_data and len(readings_data) > 0:
                            readings = readings_data[0].get("Readings", [])
                            if readings:
                                total_reading = readings[0].get("Value")
                                reading_timestamp = readings[0].get("Timestamp")
                    except Exception as err:
                        _LOGGER.warning(
                            "Failed to fetch total reading for %s: %s", device_id, err
                        )
                        total_reading = None
                        reading_timestamp = None

                    all_device_data[device_id] = {
                        "device": device,
                        "location": location,
                        "usage": usage,
                        "total_reading": total_reading,
                        "reading_timestamp": reading_timestamp,
                    }

            return all_device_data
