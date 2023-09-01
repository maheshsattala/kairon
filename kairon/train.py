import os
from urllib.parse import urljoin

import elasticapm
from loguru import logger as logging
from rasa.api import train
from rasa.model import DEFAULT_MODELS_PATH
from rasa.shared.constants import DEFAULT_CONFIG_PATH, DEFAULT_DATA_PATH, DEFAULT_DOMAIN_PATH

from kairon.exceptions import AppException
from kairon.shared.account.processor import AccountProcessor
from kairon.shared.data.constant import EVENT_STATUS
from kairon.shared.data.model_processor import ModelProcessor
from kairon.shared.data.processor import MongoProcessor
from kairon.shared.llm.factory import LLMFactory
from kairon.shared.metering.constants import MetricType
from kairon.shared.metering.metering_processor import MeteringProcessor
from kairon.shared.utils import Utility


def train_model_for_bot(bot: str):
    """
    loads bot data from mongo into individual files for training

    :param bot: bot id
    :return: model path

    """
    processor = MongoProcessor()
    nlu = processor.load_nlu(bot)
    if not nlu.training_examples:
        raise AppException("Training data does not exists!")
    domain = processor.load_domain(bot)
    stories = processor.load_stories(bot)
    multiflow_stories = processor.load_multiflow_stories(bot)
    stories = stories.merge(multiflow_stories[0])
    config = processor.load_config(bot)
    config['assistant_id'] = bot
    rules = processor.get_rules_for_training(bot)
    rules = rules.merge(multiflow_stories[1])

    directory = Utility.write_training_data(
        nlu,
        domain,
        config,
        stories,
        rules
    )

    output = os.path.join(DEFAULT_MODELS_PATH, bot)
    if not os.path.exists(output):
        os.mkdir(output)
    model = train(
        domain=os.path.join(directory, DEFAULT_DOMAIN_PATH),
        config=os.path.join(directory, DEFAULT_CONFIG_PATH),
        training_files=os.path.join(directory, DEFAULT_DATA_PATH),
        output=output,
        core_additional_arguments={"augmentation_factor": 100},
        force_training=True
    ).model
    Utility.delete_directory(directory)
    del processor
    del nlu
    del domain
    del stories
    del rules
    del multiflow_stories
    del config
    Utility.move_old_models(output, model)
    Utility.delete_models(bot)
    return model


def start_training(bot: str, user: str, token: str = None):
    """
    prevents training of the bot,
    if the training session is in progress otherwise start training

    :param reload: whether to reload model in the cache
    :param bot: bot id
    :param token: JWT token for remote model reload
    :param user: user id
    :return: model path
    """
    exception = None
    model_file = None
    training_status = None
    apm_client = None
    processor = MongoProcessor()
    try:
        apm_client = Utility.initiate_fastapi_apm_client()
        if apm_client:
            elasticapm.instrument()
            apm_client.begin_transaction(transaction_type="script")
        ModelProcessor.set_training_status(bot=bot, user=user, status=EVENT_STATUS.INPROGRESS.value)
        settings = processor.get_bot_settings(bot, user)
        settings = settings.to_mongo().to_dict()
        if settings["llm_settings"]['enable_faq']:
            llm = LLMFactory.get_instance("faq")(bot, settings["llm_settings"])
            faqs = llm.train()
            account = AccountProcessor.get_bot(bot)['account']
            MeteringProcessor.add_metrics(bot=bot, metric_type=MetricType.faq_training.value, account=account, **faqs)
        model_file = train_model_for_bot(bot)
        training_status = EVENT_STATUS.DONE.value
        agent_url = Utility.environment['model']['agent'].get('url')
        if agent_url:
            if token:
                Utility.http_request('get', urljoin(agent_url, f"/api/bot/{bot}/reload"), token, user)
    except Exception as e:
        logging.exception(e)
        training_status = EVENT_STATUS.FAIL.value
        exception = str(e)
    finally:
        if apm_client:
            apm_client.end_transaction(name=__name__, result="success")
        ModelProcessor.set_training_status(
            bot=bot,
            user=user,
            status=training_status,
            model_path=model_file,
            exception=exception,
        )
    return model_file
