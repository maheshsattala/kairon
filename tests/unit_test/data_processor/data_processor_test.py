import pytest
from mongoengine import connect
from rasa.core.training.structures import StoryGraph
from rasa.importers.rasa import Domain
from rasa.nlu.training_data import TrainingData

from bot_trainer.data_processor.data_objects import *
from bot_trainer.data_processor.processor import MongoProcessor
import os
from bot_trainer.utils import Utility

os.environ["system_file"] = "./tests/testing_data/system.yaml"


class TestMongoProcessor:
    @pytest.fixture(autouse=True)
    def init_connection(self):
        Utility.load_evironment()
        connect(Utility.environment["mongo_db"], host=Utility.environment["mongo_url"])

    def test_load_from_path(self):
        processor = MongoProcessor()
        assert (
            processor.save_from_path("tests/testing_data/initial", "tests", "testUser")
            == None
        )

    def test_load_from_path_error(self):
        processor = MongoProcessor()
        with pytest.raises(Exception):
            processor.save_from_path("tests/testing_data/error", "tests", "testUser")

    def test_load_from_path_all_sccenario(self):
        processor = MongoProcessor()
        processor.save_from_path("tests/testing_data/all", "all", "testUser")
        training_data = processor.load_nlu("all")
        assert isinstance(training_data, TrainingData) == True
        assert training_data.training_examples.__len__() == 283
        assert training_data.entity_synonyms.__len__() == 3
        assert training_data.regex_features.__len__() == 5
        assert training_data.lookup_tables.__len__() == 1
        story_graph = processor.load_stories("all")
        assert isinstance(story_graph, StoryGraph) == True
        assert story_graph.story_steps.__len__() == 13
        domain = processor.load_domain("all")
        assert isinstance(domain, Domain)
        assert domain.slots.__len__() == 8
        assert domain.templates.keys().__len__() == 21
        assert domain.entities.__len__() == 7
        assert domain.form_names.__len__() == 2
        assert domain.user_actions.__len__() == 32
        assert domain.intents.__len__() == 22
        assert not Utility.check_empty_string(
            domain.templates["utter_cheer_up"][0]["image"]
        )
        assert domain.templates["utter_did_that_help"][0]["buttons"].__len__() == 2
        assert domain.templates["utter_offer_help"][0]["custom"]
        assert domain.slots[0].type_name == "unfeaturized"

    def test_load_nlu(self):
        processor = MongoProcessor()
        training_data = processor.load_nlu("tests")
        assert isinstance(training_data, TrainingData) == True
        assert training_data.training_examples.__len__() == 43
        assert training_data.entity_synonyms.__len__() == 0
        assert training_data.regex_features.__len__() == 0
        assert training_data.lookup_tables.__len__() == 0

    def test_load_domain(self):
        processor = MongoProcessor()
        domain = processor.load_domain("tests")
        assert isinstance(domain, Domain)
        assert domain.slots.__len__() == 0
        assert domain.templates.keys().__len__() == 6
        assert domain.entities.__len__() == 0
        assert domain.form_names.__len__() == 0
        assert domain.user_actions.__len__() == 6
        assert domain.intents.__len__() == 7

    def test_load_stories(self):
        processor = MongoProcessor()
        story_graph = processor.load_stories("tests")
        assert isinstance(story_graph, StoryGraph) == True
        assert story_graph.story_steps.__len__() == 5

    def test_add_intent(self):
        processor = MongoProcessor()
        assert processor.add_intent("greeting", "tests", "testUser")
        intent = Intents.objects(bot="tests").get(name="greeting")
        assert intent.name == "greeting"

    def test_get_intents(self):
        processor = MongoProcessor()
        expected = [
            "affirm",
            "bot_challenge",
            "deny",
            "goodbye",
            "greet",
            "mood_great",
            "mood_unhappy",
            "greeting",
        ]
        actual = processor.get_intents("tests")
        assert actual.__len__() == expected.__len__()
        assert all(item["name"] in expected for item in actual)

    def test_add_intent_duplicate(self):
        processor = MongoProcessor()
        with pytest.raises(Exception):
            processor.add_intent("greeting", "tests", "testUser")

    def test_add_none_intent(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_intent(None, "tests", "testUser")

    def test_add_empty_intent(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_intent("", "tests", "testUser")

    def test_add_blank_intent(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_intent("  ", "tests", "testUser")

    def test_add_training_example(self):
        processor = MongoProcessor()
        assert processor.add_training_example("Hi", "greeting", "tests", "testUser")
        training_example = TrainingExamples.objects(bot="tests").get(
            intent="greeting", text="Hi"
        )
        assert training_example.intent == "greeting"
        assert training_example.text == "Hi"

    def test_add_same_training_example(self):
        processor = MongoProcessor()
        with pytest.raises(Exception):
            processor.add_training_example("Hi", "greeting", "tests", "testUser")

    def test_add_training_example_none_text(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_training_example(None, "greeting", "tests", "testUser")

    def test_add_training_example_empty_text(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_training_example("", "greeting", "tests", "testUser")

    def test_add_training_example_blank_text(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_training_example("  ", "greeting", "tests", "testUser")

    def test_add_training_example_none_intent(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_training_example("Hi! How are you", None, "tests", "testUser")

    def test_add_training_example_empty_intent(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_training_example("Hi! How are you", "", "tests", "testUser")

    def test_add_training_example_blank_intent(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_training_example("Hi! How are you", "  ", "tests", "testUser")

    def test_add_empty_training_example(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_training_example("", None, "tests", "testUser")

    def test_get_training_examples(self):
        processor = MongoProcessor()
        expected = ["hey", "hello", "hi", "good morning", "good evening", "hey there"]
        actual = list(processor.get_training_examples("greet", "tests"))
        assert actual.__len__() == expected.__len__()
        assert all(a_val["text"] in expected for a_val in actual)

    def test_add_training_example_with_entity(self):
        processor = MongoProcessor()
        processor.add_training_example(
            "Log a [critical issue](priority)", "get_priority", "tests", "testUser"
        )
        new_intent = Intents.objects(bot="tests").get(name="get_priority")
        new_entity = Entities.objects(bot="tests").get(name="priority")
        new_training_example = TrainingExamples.objects(bot="tests").get(
            text="Log a critical issue"
        )
        slots = Slots.objects(bot="tests")
        new_slot = slots.get(name="priority")
        assert new_intent.name == "get_priority"
        assert new_entity.name == "priority"
        assert slots.__len__() == 1
        assert new_slot.name == "priority"
        assert new_slot.type == "text"
        assert new_training_example.text == "Log a critical issue"

    def test_get_training_examples_with_entities(self):
        processor = MongoProcessor()
        processor.add_training_example(
            "Make [TKT456](ticketID) a [critical issue](priority)",
            "get_priority",
            "tests",
            "testUser",
        )
        actual = list(processor.get_training_examples("get_priority", "tests"))
        slots = Slots.objects(bot="tests")
        new_slot = slots.get(name="ticketID")
        assert any(
            [value["text"] == "Log a [critical issue](priority)" for value in actual]
        )
        assert any(
            [
                value["text"] == "Make [TKT456](ticketID) a [critical issue](priority)"
                for value in actual
            ]
        )
        assert slots.__len__() == 2
        assert new_slot.name == "ticketID"
        assert new_slot.type == "text"
        expected = ["hey", "hello", "hi", "good morning", "good evening", "hey there"]
        actual = list(processor.get_training_examples("greet", "tests"))
        assert actual.__len__() == expected.__len__()
        assert all(a_val["text"] in expected for a_val in actual)

    def test_delete_training_example(self):
        processor = MongoProcessor()
        training_examples = TrainingExamples.objects(
            bot="tests", intent="get_priority", status=True
        )
        expected_length = training_examples.__len__() - 1
        training_example = training_examples[0]
        expected_text = training_example.text
        processor.remove_document(
            TrainingExamples, training_example.id, "tests", "testUser"
        )
        new_training_examples = list(
            processor.get_training_examples(intent="get_priority", bot="tests")
        )
        assert new_training_examples.__len__() == expected_length
        assert any(
            expected_text != example["text"] for example in new_training_examples
        )

    def test_add_entity(self):
        processor = MongoProcessor()
        assert processor.add_entity("file_text", "tests", "testUser") == None
        slots = Slots.objects(bot="tests")
        new_slot = slots.get(name="file_text")
        enitity = Entities.objects(bot="tests").get(name="file_text")
        assert slots.__len__() == 3
        assert new_slot.name == "file_text"
        assert new_slot.type == "text"
        assert enitity.name == "file_text"

    def test_get_entities(self):
        processor = MongoProcessor()
        expected = ["priority", "file_text", "ticketID"]
        actual = processor.get_entities("tests")
        assert actual.__len__() == expected.__len__()
        assert all(item["name"] in expected for item in actual)

    def test_add_entity_duplicate(self):
        processor = MongoProcessor()
        with pytest.raises(Exception):
            assert processor.add_entity("file_text", "tests", "testUser")

    def test_add_none_entity(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_entity(None, "tests", "testUser")

    def test_add_empty_entity(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_entity("", "tests", "testUser")

    def test_add_blank_entity(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_entity("  ", "tests", "testUser")

    def test_add_action(self):
        processor = MongoProcessor()
        assert processor.add_action("utter_priority", "tests", "testUser") == None
        action = Actions.objects(bot="tests").get(name="utter_priority")
        assert action.name == "utter_priority"

    def test_get_actions(self):
        processor = MongoProcessor()
        expected = [
            "utter_greet",
            "utter_cheer_up",
            "utter_happy",
            "utter_goodbye",
            "utter_priority",
            "utter_did_that_help",
            "utter_iamabot",
        ]
        actual = processor.get_actions("tests")
        assert actual.__len__() == expected.__len__()
        assert all(item["name"] in expected for item in actual)

    def test_add_action_duplicate(self):
        processor = MongoProcessor()
        with pytest.raises(Exception):
            assert processor.add_action("utter_priority", "tests", "testUser") == None

    def test_add_none_action(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_action(None, "tests", "testUser")

    def test_add_empty_action(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_action("", "tests", "testUser")

    def test_add_blank_action(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_action("  ", "tests", "testUser")

    def test_add_text_response(self):
        processor = MongoProcessor()
        assert processor.add_text_response("Great", "utter_happy", "tests", "testUser")
        response = Responses.objects(
            bot="tests", name="utter_happy", text__text="Great"
        ).get()
        assert response.name == "utter_happy"
        assert response.text.text == "Great"

    def test_get_text_response(self):
        processor = MongoProcessor()
        expected = ["Great, carry on!", "Great"]
        actual = list(processor.get_response("utter_happy", "tests"))
        assert actual.__len__() == expected.__len__()
        assert all(
            item["value"]["text"] in expected
            for item in actual
            if "text" in item["value"]
        )

    def test_delete_text_response(self):
        processor = MongoProcessor()
        responses = Responses.objects(bot="tests", name="utter_happy")
        expected_length = responses.__len__() - 1
        response = responses[0]
        expected_text = response.text.text
        processor.remove_document(Responses, response.id, "tests", "testUser")
        actual = list(processor.get_response("utter_happy", "tests"))
        assert actual.__len__() == expected_length
        assert all(
            expected_text != item["value"]["text"]
            for item in actual
            if "text" in item["value"]
        )

    def test_add_text_response_duplicate(self):
        processor = MongoProcessor()
        with pytest.raises(Exception):
            processor.add_text_response("Great", "utter_happy", "tests", "testUser")

    def test_add_none_text_response(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_text_response(None, "utter_happy", "tests", "testUser")

    def test_add_empty_text_Response(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_text_response("", "utter_happy", "tests", "testUser")

    def test_add_blank_text_response(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_text_response("", "utter_happy", "tests", "testUser")

    def test_add_none_response_name(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_text_response("Greet", None, "tests", "testUser")

    def test_add_empty_response_name(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_text_response("Welcome", "", "tests", "testUser")

    def test_add_blank_response_name(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_text_response("Welcome", " ", "tests", "testUser")

    def test_add_story(self):
        processor = MongoProcessor()
        events = [
            {"name": "greet", "type": "user"},
            {"name": "utter_greet", "type": "action"},
            {"name": "mood_great", "type": "user"},
            {"name": "utter_greet", "type": "action"},
        ]
        processor.add_story("happy path", events, "tests", "testUser")

    def test_add_duplicate_story(self):
        processor = MongoProcessor()
        events = [
            {"name": "greet", "type": "user"},
            {"name": "utter_greet", "type": "action"},
            {"name": "mood_great", "type": "user"},
            {"name": "utter_greet", "type": "action"},
        ]
        with pytest.raises(Exception):
            processor.add_story("happy path", events, "tests", "testUser")

    def test_add_none_story_name(self):
        processor = MongoProcessor()
        events = [
            {"name": "greeting", "type": "user"},
            {"name": "utter_greet", "type": "action"},
            {"name": "mood_great", "type": "user"},
            {"name": "utter_greet", "type": "action"},
        ]
        with pytest.raises(ValidationError):
            processor.add_story(None, events, "tests", "testUser")

    def test_add_empty_story_name(self):
        processor = MongoProcessor()
        events = [
            {"name": "greeting", "type": "user"},
            {"name": "utter_greet", "type": "action"},
            {"name": "mood_great", "type": "user"},
            {"name": "utter_greet", "type": "action"},
        ]
        with pytest.raises(ValidationError):
            processor.add_story("", events, "tests", "testUser")

    def test_add_blank_story_name(self):
        processor = MongoProcessor()
        events = [
            {"name": "greeting", "type": "user"},
            {"name": "utter_greet", "type": "action"},
            {"name": "mood_great", "type": "user"},
            {"name": "utter_greet", "type": "action"},
        ]
        with pytest.raises(ValidationError):
            processor.add_story("  ", events, "tests", "testUser")

    def test_add_empty_story_event(self):
        processor = MongoProcessor()
        with pytest.raises(ValidationError):
            processor.add_story("happy path", [], "tests", "testUser")

    def test_add_story_start_with_action(self):
        processor = MongoProcessor()
        events = [
            {"name": "utter_greet", "type": "action"},
            {"name": "greeting", "type": "user"},
            {"name": "mood_great", "type": "user"},
            {"name": "utter_greet", "type": "action"},
        ]
        with pytest.raises(ValidationError):
            processor.add_story("greeting", events, "tests", "testUser")

    def test_add_story_end_with_user(self):
        processor = MongoProcessor()
        events = [
            {"name": "greeting", "type": "user"},
            {"name": "utter_greet", "type": "action"},
            {"name": "mood_great", "type": "user"},
        ]
        with pytest.raises(ValidationError):
            processor.add_story("greeting", events, "tests", "testUser")
