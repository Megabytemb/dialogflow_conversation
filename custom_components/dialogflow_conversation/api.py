"""Dialogflow API module."""

import logging
import os

from google.cloud import dialogflow_v2
from google.oauth2 import service_account
from google.protobuf.json_format import MessageToDict

_LOGGER = logging.getLogger(__name__)


class DialogFlow:
    """A class that interacts with DialogFlow to perform intent detection and entity manipulation."""

    def __init__(self, key_file: str):
        """Initialize the DialogFlow object with the provided key file path."""

        if not os.path.isfile(key_file):
            raise ValueError("Path to credentials file cannot be found")

        self.gcp_credentials = service_account.Credentials.from_service_account_file(
            key_file
        )
        self.project_id = self.gcp_credentials.project_id

        if not self.project_id:
            raise ValueError("Project ID not found in the provided credentials file.")

        self.session_client = dialogflow_v2.SessionsAsyncClient(
            credentials=self.gcp_credentials
        )
        self.entity_client = dialogflow_v2.EntityTypesAsyncClient(
            credentials=self.gcp_credentials
        )

    async def detect_intent(self, text: str, language_code: str, conversation_id: str):
        """Perform intent detection on the given text using DialogFlow."""
        session_path = self.session_client.session_path(
            self.project_id, conversation_id
        )

        text_input = dialogflow_v2.TextInput(text=text, language_code=language_code)

        query_input = dialogflow_v2.QueryInput(text=text_input)

        request = dialogflow_v2.DetectIntentRequest(
            session=session_path,
            query_input=query_input,
        )

        response = await self.session_client.detect_intent(request)
        resp_dict = MessageToDict(response._pb)

        params = resp_dict["queryResult"]["parameters"]
        action = resp_dict["queryResult"]["action"]

        _LOGGER.info("Detected intent: %s", action)
        _LOGGER.debug("Intent parameters: %s", params)

        return action, params

    async def get_entitytype_by_name(self, entity_name: str):
        """Retrieve the entity type with the specified name from DialogFlow."""
        if not entity_name:
            raise ValueError("Entity name cannot be empty or None.")

        parent = f"projects/{self.project_id}/agent"
        entities = await self.entity_client.list_entity_types(parent=parent)

        async for entity in entities:
            if entity.display_name == entity_name:
                return entity

        # if we got here, it doesn't exist yet, so we'll create it.
        entity_type = dialogflow_v2.EntityType(
            kind=dialogflow_v2.EntityType.Kind.KIND_MAP,
            display_name=entity_name,
        )

        entity_type = await self.entity_client.create_entity_type(
            parent=parent, entity_type=entity_type
        )

        _LOGGER.info("Created new entity type: %s", entity_name)

        return entity_type

    async def replace_entity_values(
        self, entity_name, entity_values: dict[str, list[str]]
    ):
        """Replace the values of the specified entity in DialogFlow with the given entity values."""

        if not isinstance(entity_values, dict):
            raise TypeError("Entity values must be provided as a dictionary.")

        entities = []

        for key, value in entity_values.items():
            if not isinstance(key, str) or not isinstance(value, list):
                raise TypeError(
                    "Entity values must be a dictionary with string keys and list values."
                )

            entity = dialogflow_v2.EntityType.Entity(
                value=key,
                synonyms=value,
            )
            entities.append(entity)

        entity_type = await self.get_entitytype_by_name(entity_name)
        entity_type.entities = entities

        entity_type = await self.entity_client.update_entity_type(
            entity_type=entity_type
        )
        _LOGGER.info(
            "Pushed %s entities to Dialogflow entyty %s",
            len(entity_values),
            entity_name,
        )

        return entity_type
