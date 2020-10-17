from random import randint

import requests
import vk_api
from pony.orm import db_session
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import logging
import handlers
from models import UserState, Ticket
try:
    import settings
except ImportError:
    exit('DO cp settings.py.default settings.py and set token')

log = logging.getLogger('bot')

def configure_logging():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter('%(levelname)s %(message)s'))
    file_handler = logging.FileHandler('bot.log', encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    log.addHandler(stream_handler)
    log.addHandler(file_handler)
    log.setLevel(logging.DEBUG)
    stream_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.DEBUG)



class Bot:
    """
    Echo bot for vk.com
    """

    def __init__(self, group_id, token):
        """
            :param group_id: vk group id
            :param token: secret token
        """

        self.group_id = group_id
        self.token = token
        self.vk = vk_api.VkApi(token=self.token)
        self.long_poller = VkBotLongPoll(self.vk, self.group_id)
        self.api = self.vk.get_api()

    def run(self):
        """Запуск бота"""
        for event in self.long_poller.listen():
            try:
                self.on_event(event)
            except Exception as err:
                log.exception('error')

    @db_session
    def on_event(self, event):
        """
        :param event: VkBotMessageEvent object
        :return: NONE
        """
        if event.type != VkBotEventType.MESSAGE_NEW:
            log.debug('Cannot handle this even %s', event.type)
            return

        user_id = event.object.peer_id
        text = event.object.text
        state = UserState.get(user_id=str(user_id))
        if state is not None:
            self.continue_scenario(text=text, state=state, user_id=user_id)
        else:
            # search intent
            for intent in settings.INTENTS:
                log.debug(f'User get {intent}')
                if any(token in text.lower() for token in intent['tokens']):
                    if intent['answer']:
                        self.send_text(intent['answer'], user_id)
                    else:
                        self.start_scenario(user_id, intent['scenario'], text)
                    break
            else:
                self.send_text(settings.DEFAULT_ANSWER, user_id)

    def send_file(self, file, user_id):
        upload_url = self.api.docs.getMessagesUploadServer(peer_id=user_id)['upload_url']
        upload_data = requests.post(url=upload_url, files={'file': open('flights.csv', 'rb')}).json()
        result = self.api.docs.save(**upload_data)
        owner_id = result['doc']['owner_id']
        media_id = result['doc']['id']
        attachment = f'doc{owner_id}_{media_id}'
        self.api.messages.send(
            attachment=attachment,
            random_id=randint(0, 2 ** 20),
            peer_id=user_id,
        )

    def send_step(self, step, user_id, text, context):
        if 'text' in step:
            self.send_text(step['text'].format(**context), user_id)
        if 'csvfile' in step:
            handler = getattr(handlers, step['csvfile'])
            csvfile = handler(text, context)
            self.send_file(csvfile, user_id)

    def send_text(self, text_to_send, user_id):
        self.api.messages.send(
            message=text_to_send,
            random_id=randint(0, 2 ** 20),
            peer_id=user_id,
        )

    def start_scenario(self, user_id, scenario_name, text):
        scenario = settings.SCENARIOS[scenario_name]
        first_step = scenario['first_step']
        step = scenario['steps'][first_step]
        self.send_step(step, user_id, text, context={})
        UserState(user_id=str(user_id), scenario_name=scenario_name, step_name=first_step, context={})

    def continue_scenario(self, text, state, user_id):
        steps = settings.SCENARIOS[state.scenario_name]['steps']
        step = steps[state.step_name]
        handler = getattr(handlers, step['handler'])
        if handler(text=text, context=state.context):
            # next step
            next_step = steps[step['next_step']]
            self.send_step(next_step, user_id, text, state.context)
            if next_step['next_step']:
                # switch to the next step
                state.step_name = step['next_step']
            else:
                # finish scenario)
                log.info(state.context)
                Ticket(departure_airport=state.context['departure_airport'],
                       arrival_airport=state.context['arrival_airport'],
                       date=state.context['date'])
                state.delete()

        else:
            # retry current step
            text_to_send = step['failure_text'].format(**state.context)
            self.send_text(text_to_send, user_id)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    configure_logging()
    bot = Bot(group_id=settings.GROUP_ID, token=settings.TOKEN)
    bot.run()
