"""Constants for the VandCenter Syd integration."""
from datetime import timedelta

DOMAIN = "vandcenter_syd"
CONF_EMAIL = "email"
CONF_PASSWORD = "password"
CONF_TOKEN = "token"
CONF_TOKEN_EXPIRES = "token_expires"

API_BASE = "https://vandcenter.smartforsyning.dk/api"
UPDATE_INTERVAL = timedelta(hours=6)  # Don't hammer their API
