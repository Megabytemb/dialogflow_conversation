# Dialogflow_Conversation

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

[![hacs][hacsbadge]][hacs]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

The Dialogflow Conversation integration is a custom component for Home Assistant, providing a seamless bridge between your Home Assistant setup and the Dialogflow conversational AI platform by Google​​. It leverages the capabilities of Dialogflow to make your home smart devices more interactive and responsive to natural language commands.

**This integration will set up the following platforms.**

Platform | Description
-- | --
`conversation` | Used to connect the Home Assistant Assist pipeline to Dialogflow.
`intent` | Intent recognition after dialogflow response.

## Installation

### Installation through HACS
1. Go to the HACS page on your Home Assistant instance.
2. Click on "Integrations".
3. Click on the three dots in the top right corner and select "Custom repositories".
4. Add https://github.com/Megabytemb/dialogflow_conversation as a custom repository and select "Integration" as the category.
5. Click "Add".
6. The dialogflow_conversation integration will now be available for installation in HACS.

### Manual installation

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `dialogflow_conversation`.
1. Download _all_ the files from the `custom_components/dialogflow_conversation/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Dialogflow_Conversation"

## Configuration is done in the UI

In addition to the UI configuration, you can also customize which entities are synced to Dialogflow by defining filters in your configuration.yaml file. This can be done using the filter configuration option under the dialogflow_conversation domain.

Here is an example of how to configure a filter:

```
dialogflow_conversation:
  filter:
    include_domains:
      - input_boolean
```

Please note that the `filter` configuration uses the same format as Home Assistant's entity filter configuration. You can include or exclude entities by domain, entity_id, or even by using glob patterns. For more details on the filter configuration, you can refer to the [Homekit integration documentation](https://www.home-assistant.io/integrations/homekit/#manual-configuration) on the Home Assistant website.

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[dialogflow_conversation]: https://github.com/Megabytemb/dialogflow_conversation
[commits-shield]: https://img.shields.io/github/commit-activity/y/Megabytemb/dialogflow_conversation.svg?style=for-the-badge
[commits]: https://github.com/Megabytemb/dialogflow_conversation/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/Megabytemb/dialogflow_conversation.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/Megabytemb/dialogflow_conversation.svg?style=for-the-badge
[releases]: https://github.com/Megabytemb/dialogflow_conversation/releases
