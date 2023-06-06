"""Agent Module for Dialogflow conversation."""

import logging

from homeassistant.components import conversation
from homeassistant.core import HassJob, HomeAssistant
from homeassistant.helpers import entity_registry as er, intent
from homeassistant.helpers.event import async_call_later
from homeassistant.util import ulid

from .api import DialogFlow
from .const import DIALOGFLOW_ENTITY_NAME, DOMAIN, PUSH_ENTITIES_INTERVAL

_LOGGER = logging.getLogger(__name__)


class DialogflowAgent(conversation.AbstractConversationAgent):
    """Dialogflow conversation agent."""

    def __init__(self, hass: HomeAssistant, df_client: DialogFlow) -> None:
        """Initialize the agent."""
        self.hass = hass
        self._unsub_entities_updates = None

        self.df_client: DialogFlow = df_client

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
        text = user_input.text
        conversation_id = user_input.conversation_id
        if conversation_id is None:
            conversation_id = ulid.ulid()

        _LOGGER.info(f"Sending text to dialogflow: {text}")

        intent_resp, params = await self.df_client.detect_intent(
            text=text,
            language_code=language_code,
            conversation_id=conversation_id,
        )

        _LOGGER.info(f"Got this intent pack: {intent_resp}")

        intent_response = await self._handle_intent(
            user_input,
            intent_resp,
            params,
            conversation_id=conversation_id,
        )

        return conversation.ConversationResult(
            response=intent_response, conversation_id=conversation_id
        )

    async def _handle_intent(
        self, user_input, intent_type, params, conversation_id=None
    ):
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

    async def send_entities_to_dialogflow(self):
        """Upload entities to Dialogflow based on Filter."""
        _LOGGER.info("Updating Entities in DialogFlow HAEntity")
        ent_reg = er.async_get(self.hass)
        entity_values = {}
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

            synonyms += entity_entry.aliases

            entity_values[entity_entry.entity_id] = synonyms

        await self.df_client.replace_entity_values(
            DIALOGFLOW_ENTITY_NAME, entity_values=entity_values
        )

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
