from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch, Mock, ANY

from pony.orm import db_session, rollback
from vk_api.bot_longpoll import VkBotMessageEvent
from bot import Bot

try:
    import settings
except ImportError:
    exit('DO cp settings.py.default settings.py and set token')


def isolate_db(test_func):
    def wrapper(*args, **kwargs):
        with db_session:
            test_func(*args, **kwargs)
            rollback()

    return wrapper


class Test1(TestCase):
    RAW_EVENT = {'type': 'message_new', 'object':
        {'date': 1599384788,
         'from_id': 271883001,
         'id': 26, 'out': 0,
         'peer_id': 271883001,
         'text': 'Привет',
         'conversation_message_id': 23,
         'fwd_messages': [],
         'important': False,
         'random_id': 0,
         'attachments': [],
         'is_hidden': False},
                 'group_id': 198143547, 'event_id': '486a8cc0c8ef3f2f3eec2ef126452c03c2308918'}

    def test_run(self):
        count = 5
        obj = {'a': 1}
        events = [obj] * count
        long_poller_mock = Mock(return_value=events)
        long_poller_listen_mock = Mock()
        long_poller_listen_mock.listen = long_poller_mock
        with patch('bot.vk_api.VkApi'):
            with patch('bot.VkBotLongPoll', return_value=long_poller_listen_mock):
                bot = Bot('', '')
                bot.on_event = Mock()
                bot.run()

                bot.on_event.assert_called()
                bot.on_event.assert_any_call(obj)
                assert bot.on_event.call_count == count

    INPUTS = [
        'How is going?',
        'Hi',
        'Bye',
        'Thanks',
        '/ticket',
        'Domodedovo',
        '123',
        'Dubai International',
        '2020-10-15'
    ]
    EXPECTED_OUTPUTS = [
        settings.DEFAULT_ANSWER,
        settings.INTENTS[0]['answer'],
        settings.INTENTS[1]['answer'],
        settings.INTENTS[2]['answer'],
        settings.SCENARIOS['flight_search']['steps']['step1']['text'],
        settings.SCENARIOS['flight_search']['steps']['step2']['text'],
        settings.SCENARIOS['flight_search']['steps']['step2']['failure_text'],
        settings.SCENARIOS['flight_search']['steps']['step3']['text'],
        settings.SCENARIOS['flight_search']['steps']['step4']['text']
    ]

    def test_run_ok(self):
        send_mock = Mock()
        api_mock = Mock()
        api_mock.messages.send = send_mock

        events = []
        for input_text in self.INPUTS:
            event = deepcopy(self.RAW_EVENT)
            event['object']['text'] = input_text
            events.append(VkBotMessageEvent(event))

        long_poller_mock = Mock()
        long_poller_mock.listen = Mock(return_value=events)

        with patch('bot.VkBotLongPoll', return_value=long_poller_mock):
            bot = Bot('', '')
            bot.api = api_mock
            bot.run()

        assert send_mock.call_count == len(self.INPUTS)
        real_outputs = []
        for call in send_mock.call_args_list:
            args, kwargs = call
            real_outputs.append(kwargs['message'])
        for index, (real, expec) in enumerate(zip(real_outputs, self.EXPECTED_OUTPUTS)):
            print('Ввод: ', self.INPUTS[index])
            print('-' * 50)
            print('Что пришло - ', real)
            print('-' * 50)
            print('Что ожидалось - ', expec)
            print('-' * 50)
            print('Всё верно? - ', real == expec)
            print('=' * 50)

        assert real_outputs == self.EXPECTED_OUTPUTS
