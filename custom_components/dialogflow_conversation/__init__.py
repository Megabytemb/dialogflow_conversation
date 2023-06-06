"""Custom integration to integrate dialogflow_conversation with Home Assistant.

For more details about this integration, please refer to
https://github.com/Megabytemb/dialogflow_conversation
"""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED, SERVICE_RELOAD
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import service
from homeassistant.helpers.entityfilter import FILTER_SCHEMA
from homeassistant.helpers.reload import async_integration_yaml_config
from homeassistant.helpers.typing import ConfigType

from .agent import DialogflowAgent
from .api import DialogFlow
from .const import CONF_FILTER, CONF_KEY_FILE, DOMAIN

_LOGGER = logging.getLogger(__name__)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_FILTER, default={}): FILTER_SCHEMA,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_reload(hass: HomeAssistant, service_call: ServiceCall) -> None:
    """Handle reload service call."""
    new_config = await async_integration_yaml_config(hass, DOMAIN)

    if not new_config or DOMAIN not in new_config:
        entity_filter = FILTER_SCHEMA({})
    else:
        conf = new_config[DOMAIN]
        entity_filter = conf[CONF_FILTER]
        hass.data[DOMAIN]["entity_filter"] = entity_filter

    if (agent := hass.data[DOMAIN].get("agent")) is not None:
        await agent.send_entities_to_dialogflow()

    return


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Splunk component."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN in config:
        conf = config[DOMAIN]
        entity_filter = conf[CONF_FILTER]
    else:
        entity_filter = FILTER_SCHEMA({})

    hass.data[DOMAIN]["entity_filter"] = entity_filter

    async def _handle_reload(servie_call: ServiceCall) -> None:
        return await async_reload(hass, servie_call)

    service.async_register_admin_service(
        hass,
        DOMAIN,
        SERVICE_RELOAD,
        _handle_reload,
    )

    return True


# https://developers.hom e-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})

    conf = entry.data
    key_file = conf.get(CONF_KEY_FILE)
    key_file = hass.config.path(key_file)

    df_client = DialogFlow(key_file)

    agent = DialogflowAgent(hass, df_client)
    hass.data[DOMAIN]["agent"] = agent
    await agent.schedule_send_entities()

    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STARTED, agent.send_entities_to_dialogflow()
    )

    conversation.async_set_agent(hass, entry, agent)
