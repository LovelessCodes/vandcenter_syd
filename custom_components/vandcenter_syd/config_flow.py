"""Config flow for VandCenter Syd."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    API_BASE,
    CONF_TOKEN,
    DOMAIN,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_TOKEN_EXPIRES,
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            session = async_get_clientsession(self.hass)

            # Test login
            try:
                resp = await session.post(
                    f"{API_BASE}/Customer/login",
                    json={"MatchTag": None, "Email": email, "Password": password},
                )
                if resp.status == 200:
                    data = await resp.json()
                    return self.async_create_entry(
                        title="VandCenter Syd",
                        data={
                            CONF_EMAIL: email,
                            CONF_PASSWORD: password,
                            CONF_TOKEN: data["AuthToken"],
                            CONF_TOKEN_EXPIRES: data["ExpiresIn"],
                        },
                    )
                errors["base"] = "invalid_auth"
            except Exception:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
