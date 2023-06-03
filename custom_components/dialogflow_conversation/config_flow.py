"""Adds config flow for dialogflow conversation."""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.helpers import selector
import voluptuous as vol

from .const import CONF_KEY_FILE, DEFAULT_KEY_FILE, DOMAIN


class DialogflowConversationFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for dialogflow conversation."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_KEY_FILE],
                data=user_input,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_KEY_FILE,
                        default=(user_input or {}).get(DEFAULT_KEY_FILE),
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.TEXT
                        ),
                    ),
                }
            ),
            errors=_errors,
        )
