"""Constants for dialogflow_conversation."""
from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

################################
# Do not change! Will be set by release workflow
INTEGRATION_VERSION = "main"  # git tag will be used
MIN_REQUIRED_HA_VERSION = "0.0.0"  # set min required version in hacs.json
################################

NAME = "Dialogflow Conversation"
DOMAIN = "dialogflow_conversation"
CONF_KEY_FILE = "key_file"
CONF_FILTER = "filter"

DEFAULT_KEY_FILE = "keys/sa.json"

PUSH_ENTITIES_INTERVAL = 3600

DIALOGFLOW_ENTITY_NAME = "HAEntity"
