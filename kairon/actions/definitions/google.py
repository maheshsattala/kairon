from typing import Text, Dict, Any

from googlesearch import search
from loguru import logger
from mongoengine import DoesNotExist
from rasa_sdk import Tracker
from rasa_sdk.executor import CollectingDispatcher

from kairon.actions.definitions.base import ActionsBase
from kairon.shared.actions.data_objects import GoogleSearchAction, ActionServerLogs
from kairon.shared.actions.exception import ActionFailure
from kairon.shared.actions.models import ActionType
from kairon.shared.actions.utils import ActionUtility
from kairon.shared.constants import KAIRON_USER_MSG_ENTITY, KaironSystemSlots


class ActionGoogleSearch(ActionsBase):

    def __init__(self, bot: Text, name: Text):
        """
        Initialize Google search action.

        @param bot: bot id
        @param name: action name
        """
        self.bot = bot
        self.name = name
        self.__response = None
        self.__is_success = False

    def retrieve_config(self):
        """
        Fetch Google search action configuration parameters from the database.

        :return: GoogleSearchAction containing configuration for the action as a dict.
        """
        try:
            action = GoogleSearchAction.objects(bot=self.bot, name=self.name, status=True).get().to_mongo().to_dict()
            logger.debug("google_search_action_config: " + str(action))
        except DoesNotExist as e:
            logger.exception(e)
            raise ActionFailure("No Google search action found for given action and bot")
        return action

    async def execute(self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]):
        """
        Retrieves action config and executes it.
        Information regarding the execution is logged in ActionServerLogs.

        @param dispatcher: Client to send messages back to the user.
        @param tracker: Tracker object to retrieve slots, events, messages and other contextual information.
        @param domain: Bot domain
        :return: Dict containing slot name as keys and their values.
        """
        slots_set = {}
        results = None
        exception = None
        status = "SUCCESS"
        latest_msg = tracker.latest_message.get('text')
        action_config = self.retrieve_config()
        bot_response = action_config.get("failure_response")
        api_key = action_config.get('api_key')
        perform_global_search = action_config.get('perform_global_search')
        try:
            if not ActionUtility.is_empty(latest_msg) and latest_msg.startswith("/"):
                user_msg = next(tracker.get_latest_entity_values(KAIRON_USER_MSG_ENTITY), None)
                if not ActionUtility.is_empty(user_msg):
                    latest_msg = user_msg
            tracker_data = ActionUtility.build_context(tracker)
            api_key = ActionUtility.retrieve_value_for_custom_action_parameter(tracker_data, api_key, self.bot)
            if not ActionUtility.is_empty(latest_msg):
                if perform_global_search:
                    results = list(search("How to add task plan site: https://nimblework.com",
                                          num_results=10, advanced=True))
                else:
                    results = ActionUtility.perform_google_search(
                        api_key, action_config['search_engine_id'], latest_msg, num=action_config.get("num_results")
                    )
                if results:
                    bot_response = ActionUtility.format_search_result(results)
                    self.__response = bot_response
                    self.__is_success = True
                    if not ActionUtility.is_empty(action_config.get('set_slot')):
                        slots_set.update({action_config['set_slot']: bot_response})
        except Exception as e:
            logger.exception(e)
            exception = str(e)
            status = "FAILURE"
        finally:
            ActionServerLogs(
                type=ActionType.google_search_action.value,
                intent=tracker.get_intent_of_latest_message(skip_fallback_intent=False),
                action=action_config['name'],
                google_response=results,
                bot_response=bot_response,
                sender=tracker.sender_id,
                bot=tracker.get_slot("bot"),
                exception=exception,
                status=status,
                user_msg=tracker.latest_message.get('text')
            ).save()
        if action_config.get('dispatch_response', True):
            dispatcher.utter_message(bot_response)
        slots_set.update({KaironSystemSlots.kairon_action_response.value: bot_response})
        return slots_set

    @property
    def is_success(self):
        return self.__is_success

    @property
    def response(self):
        return self.__response
