import os
import shutil
from unittest.mock import patch

import bson
import pytest
from rasa.core.lock_store import InMemoryLockStore
from redis.client import Redis

from kairon.shared.utils import Utility
from kairon.chat.agent_processor import AgentProcessor
from kairon.exceptions import AppException
from mock import patch
from deepdiff import DeepDiff
from mongoengine import connect

class TestAgentProcessor:

    @pytest.fixture(autouse=True, scope='class')
    def init_connection(self):
        from rasa import train

        os.environ["system_file"] = "./tests/testing_data/system.yaml"
        Utility.load_environment()
        connect(**Utility.mongoengine_connection())
        bot = bson.ObjectId().__str__()
        pytest.bot = bot
        model_path = os.path.join('models', bot)
        if not os.path.exists(model_path):
            os.mkdir(model_path)
        train(
            domain='tests/testing_data/model_tester/domain.yml',
            config='tests/testing_data/model_tester/config.yml',
            training_files=['tests/testing_data/model_tester/nlu_with_entities/nlu.yml',
                            'tests/testing_data/model_tester/training_stories_success/stories.yml'],
            output=model_path,
            core_additional_arguments={"augmentation_factor": 100},
            force_training=True
        )
        yield None
        shutil.rmtree(model_path)

    def test_reload(self):
        assert not AgentProcessor.cache_provider.get(pytest.bot)

        AgentProcessor.reload(pytest.bot)
        model = AgentProcessor.cache_provider.get(pytest.bot)
        assert model
        assert isinstance(model.lock_store, InMemoryLockStore)

    def test_reload_model_with_lock_store_config(self):
        redis_config = {'url': 'rediscloud', "password": "password", "port": 6999, "db": 5}
        with patch.dict(Utility.environment['lock_store'], redis_config):
            AgentProcessor.reload(pytest.bot)
            model = AgentProcessor.cache_provider.get(pytest.bot)
            assert model
            assert isinstance(model.lock_store.red, Redis)
            assert model.lock_store.key_prefix == f'{pytest.bot}:lock:'
            assert model.lock_store.red.connection_pool.connection_kwargs['password'] == redis_config['password']
            assert (
                model.lock_store.red.connection_pool.connection_kwargs["username"]
                == redis_config.get("username")
            )
            assert (
                model.lock_store.red.connection_pool.connection_kwargs["db"]
                == redis_config["db"]
            )
            assert (
                model.lock_store.red.connection_pool.connection_kwargs["port"]
                == redis_config["port"]
            )

            assert (
                model.lock_store.red.connection_pool.connection_kwargs["host"]
                == redis_config["url"]
            )

        redis_config = {'url': 'rediscloud'}
        with patch.dict(Utility.environment['lock_store'], redis_config):
            AgentProcessor.reload(pytest.bot)
            model = AgentProcessor.cache_provider.get(pytest.bot)
            assert model
            assert isinstance(model.lock_store.red, Redis)
            assert model.lock_store.key_prefix == f'{pytest.bot}:lock:'
            assert (
                model.lock_store.red.connection_pool.connection_kwargs["password"]
                == redis_config.get("password")
            )
            assert (
                model.lock_store.red.connection_pool.connection_kwargs["username"]
                == redis_config.get("username")
            )
            assert (
                model.lock_store.red.connection_pool.connection_kwargs["db"] == 1
            )
            assert (
                model.lock_store.red.connection_pool.connection_kwargs["port"]
                == 6379
            )
            
            assert (
                model.lock_store.red.connection_pool.connection_kwargs["host"] == redis_config["url"]
            )

    def test_reload_exception(self):
        assert not AgentProcessor.cache_provider.get('test_user')

        with pytest.raises(AppException) as e:
            AgentProcessor.reload('test_user')
        assert str(e).__contains__("Bot has not been trained yet!")

    def test_get_agent_not_exists(self):
        with pytest.raises(AppException) as e:
            AgentProcessor.get_agent('test_user')
        assert str(e).__contains__("Bot has not been trained yet!")

    def test_get_agent(self):
        assert AgentProcessor.get_agent(pytest.bot)

    def test_get_agent_not_cached(self):
        assert AgentProcessor.get_agent(pytest.bot)

    def test_get_agent_custom_metric_apm_disabled(self):
        assert AgentProcessor.get_agent(pytest.bot)
        assert AgentProcessor.cache_provider.len() >= 1

    def test_get_agent_custom_metric_apm_enabled(self):

        with patch.dict(Utility.environment["elasticsearch"], {"enable": True, 'service_name': 'kairon', 'apm_server_url': 'http://localhost:8082'}):
            assert AgentProcessor.get_agent(pytest.bot)
            assert AgentProcessor.cache_provider.len() >= 1
