"""Config flow for Roborock Q10 integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL

from roborock.exceptions import (
    RoborockAccountDoesNotExist,
    RoborockInvalidCode,
    RoborockTooFrequentCodeRequests,
)
from roborock.web_api import RoborockApiClient

from .const import CONF_USER_DATA, CONF_VERIFICATION_CODE, DOMAIN

_LOGGER = logging.getLogger(__name__)


class RoborockQ10ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Roborock Q10."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._email: str | None = None
        self._client: RoborockApiClient | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: Collect email and request verification code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._client = RoborockApiClient(username=self._email)

            try:
                await self._client.request_code()
            except RoborockAccountDoesNotExist:
                errors["base"] = "invalid_email"
            except RoborockTooFrequentCodeRequests:
                errors["base"] = "too_frequent_requests"
            except Exception:
                _LOGGER.exception("Unexpected error requesting code")
                errors["base"] = "unknown"
            else:
                return await self.async_step_code()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_EMAIL): str,
                }
            ),
            errors=errors,
        )

    async def async_step_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: Collect verification code and authenticate."""
        errors: dict[str, str] = {}

        if user_input is not None:
            code = user_input[CONF_VERIFICATION_CODE]

            try:
                user_data = await self._client.code_login(int(code))
            except RoborockInvalidCode:
                errors["base"] = "invalid_code"
            except Exception:
                _LOGGER.exception("Unexpected error during login")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_data.rruid)
                self._abort_if_unique_id_configured()

                # Serialize user_data for storage
                stored_data = {
                    "rruid": user_data.rruid,
                    "token": user_data.token,
                    "region": user_data.region,
                    "country_code": user_data.countrycode,
                    "rriot": {
                        "u": user_data.rriot.u,
                        "s": user_data.rriot.s,
                        "h": user_data.rriot.h,
                        "k": user_data.rriot.k,
                        "r": {
                            "r": user_data.rriot.r.r,
                            "a": user_data.rriot.r.a,
                            "m": user_data.rriot.r.m,
                            "l": user_data.rriot.r.l,
                        },
                    },
                }

                return self.async_create_entry(
                    title=self._email,
                    data={
                        CONF_EMAIL: self._email,
                        CONF_USER_DATA: stored_data,
                    },
                )

        return self.async_show_form(
            step_id="code",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_VERIFICATION_CODE): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle reauthentication."""
        self._email = entry_data[CONF_EMAIL]
        self._client = RoborockApiClient(username=self._email)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm reauth and request a new code."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await self._client.request_code()
            except Exception:
                _LOGGER.exception("Unexpected error requesting code for reauth")
                errors["base"] = "unknown"
            else:
                return await self.async_step_code()

        return self.async_show_form(
            step_id="reauth_confirm",
            errors=errors,
        )
