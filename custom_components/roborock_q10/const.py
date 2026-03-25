"""Constants for Roborock Q10 integration."""

from homeassistant.const import Platform

DOMAIN = "roborock_q10"

CONF_USER_DATA = "user_data"
CONF_VERIFICATION_CODE = "code"

PLATFORMS = [Platform.VACUUM, Platform.SENSOR]
