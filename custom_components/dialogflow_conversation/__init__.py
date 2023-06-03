"""Custom integration to integrate dialogflow_conversation with Home Assistant.

For more details about this integration, please refer to
https://github.com/Megabytemb/dialogflow_conversation
"""
from __future__ import annotations

import logging
import os

from google.cloud import dialogflow_v2
from google.oauth2 import service_account
from google.protobuf.json_format import MessageToDict
from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HassJob, HomeAssistant
from homeassistant.helpers import entity_registry as er, intent
from homeassistant.helpers.entityfilter import FILTER_SCHEMA
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import ulid
import voluptuous as vol

from .const import (
    CONF_FILTER,
    CONF_KEY_FILE,
    DIALOGFLOW_ENTITY_NAME,
    DOMAIN,
    PUSH_ENTITIES_INTERVAL,
)

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


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Splunk component."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN in config:
        conf = config[DOMAIN]
        entity_filter = conf[CONF_FILTER]
    else:
        entity_filter = FILTER_SCHEMA({})

    hass.data[DOMAIN]["entity_filter"] = entity_filter

    return True


# https://developers.hom e-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    hass.data.setdefault(DOMAIN, {})

    conf = entry.data
    key_file = conf.get(CONF_KEY_FILE)

    agent = DialogflowAgent(hass, key_file)
    await agent.schedule_send_entities()

    hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STARTED, agent.send_entities_to_dialogflow()
    )

    conversation.async_set_agent(hass, entry, agent)


class DialogflowAgent(conversation.AbstractConversationAgent):
    """Dialogflow conversation agent."""

    def __init__(self, hass: HomeAssistant, key_file: str) -> None:
        """Initialize the agent."""
        self.hass = hass
        key_file = hass.config.path(key_file)
        self._unsub_entities_updates = None

        if not os.path.isfile(key_file):
            _LOGGER.error("Path to credentials file cannot be found")
            return False

        self.gcp_credentials = service_account.Credentials.from_service_account_file(
            key_file
        )
        self.project_id = self.gcp_credentials.project_id

        self.session_client = dialogflow_v2.SessionsAsyncClient(
            credentials=self.gcp_credentials
        )
        self.entity_client = dialogflow_v2.EntityTypesAsyncClient(
            credentials=self.gcp_credentials
        )

    @property
    def attribution(self):
        """Return the attribution."""
        return {
            "name": "Powered by Dialogflow",
            "url": "https://cloud.google.com/dialogflow",
        }

    @property
    def supported_languages(self) -> list[str]:
        """Return a list of supported languages."""
        return ["en"]  # Replace with the supported languages for your agent

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        language_code = user_input.language
        text_input = dialogflow_v2.TextInput(
            text=user_input.text, language_code=language_code
        )

        conversation_id = user_input.conversation_id
        if conversation_id is None:
            conversation_id = ulid.ulid()

        session_path = self.session_client.session_path(
            self.project_id, conversation_id
        )

        query_input = dialogflow_v2.QueryInput(text=text_input)

        request = dialogflow_v2.DetectIntentRequest(
            session=session_path,
            query_input=query_input,
        )

        response = await self.session_client.detect_intent(request)
        resp_dict = MessageToDict(response._pb)
        params = resp_dict["queryResult"]["parameters"]
        action = resp_dict["queryResult"]["action"]

        intent_response = await self._handle_intent(
            user_input,
            action,
            params,
            conversation_id=conversation_id,
        )

        return conversation.ConversationResult(
            response=intent_response, conversation_id=conversation_id
        )

    async def _handle_intent(self, user_input, intent_type, params, conversation_id):
        language = user_input.language or self.hass.config.language

        try:
            intent_response = await intent.async_handle(
                self.hass,
                DOMAIN,
                intent_type,
                params,
                user_input.text,
                user_input.context,
                language,
                assistant=DOMAIN,
            )
        except intent.IntentHandleError:
            _LOGGER.exception("Intent handling error")
            return _make_error_result(
                language,
                intent.IntentResponseErrorCode.FAILED_TO_HANDLE,
                "Intent handling error",
                conversation_id,
            )
        except intent.IntentUnexpectedError:
            _LOGGER.exception("Unexpected intent error")
            return _make_error_result(
                language,
                intent.IntentResponseErrorCode.UNKNOWN,
                "Unexpected intent error",
                conversation_id,
            )

        return intent_response

    async def schedule_send_entities(self):
        """Set up loop to push entities to DialogFlow."""

        async def _send_updates(*_) -> None:
            await self.send_entities_to_dialogflow()
            await self.schedule_send_entities()

        self._unsub_entities_updates = async_call_later(
            self.hass,
            PUSH_ENTITIES_INTERVAL,
            HassJob(_send_updates, cancel_on_shutdown=True),
        )

    async def _get_entity_type(self) -> dialogflow_v2.EntityType | None:
        """Get Entity Type from DialogFlow."""
        parent = f"projects/{self.project_id}/agent"
        entities = await self.entity_client.list_entity_types(parent=parent)

        async for entity in entities:
            if entity.display_name == DIALOGFLOW_ENTITY_NAME:
                return entity
        # if we got here, it doesn't exist yet, so we'll create it.

        entity_type = dialogflow_v2.EntityType(
            kind=dialogflow_v2.EntityType.Kind.KIND_MAP,
            display_name=DIALOGFLOW_ENTITY_NAME,
        )

        entity_type = await self.entity_client.create_entity_type(
            parent=parent, entity_type=entity_type
        )

        return entity_type

    async def send_entities_to_dialogflow(self):
        """Upload entities to Dialogflow based on Filter."""
        _LOGGER.info("Updating Entities in DialogFlow HAEntity")
        ent_reg = er.async_get(self.hass)
        entities = []
        entity_filter = self.hass.data[DOMAIN]["entity_filter"]

        if entity_filter.empty_filter is True:
            return

        for entity_entry in ent_reg.entities.values():
            if not entity_filter(entity_entry.entity_id):
                continue

            synonyms = [entity_entry.entity_id]
            if entity_entry.name is not None:
                synonyms.append(entity_entry.name)
            elif entity_entry.original_name is not None:
                synonyms.append(entity_entry.original_name)

            entity = dialogflow_v2.EntityType.Entity(
                value=entity_entry.entity_id,
                synonyms=synonyms,
            )

            entities.append(entity)

        entity_type = await self._get_entity_type()
        entity_type.entities = entities

        await self.entity_client.update_entity_type(entity_type=entity_type)
        _LOGGER.info("Updated Entities in DialogFlow HAEntity")

        return True


def _make_error_result(
    language: str,
    error_code: intent.IntentResponseErrorCode,
    response_text: str,
    conversation_id: str | None = None,
) -> conversation.ConversationResult:
    """Create conversation result with error code and text."""
    response = intent.IntentResponse(language=language)
    response.async_set_error(error_code, response_text)

    return conversation.ConversationResult(response, conversation_id)
