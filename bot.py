from random import randint

import vk_api
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
            text_to_send = self.continue_scenario(text=text, state=state)
        else:
            # search intent
            for intent in settings.INTENTS:
                log.debug(f'User get {intent}')
                if any(token in text.lower() for token in intent['tokens']):
                    if intent['answer']:
                        text_to_send = intent['answer']
                    else:
                        text_to_send = self.start_scenario(user_id, intent['scenario'])
                    break
            else:
                text_to_send = settings.DEFAULT_ANSWER

        self.api.messages.send(
            message=text_to_send,
            random_id=randint(0, 2 ** 20),
            peer_id=user_id,
        )

    def start_scenario(self, user_id, scenario_name):
        scenario = settings.SCENARIOS[scenario_name]
        first_step = scenario['first_step']
        step = scenario['steps'][first_step]
        text_to_send = step['text']
        UserState(user_id=str(user_id), scenario_name=scenario_name, step_name=first_step, context={})
        return text_to_send

    def continue_scenario(self, text, state):
        steps = settings.SCENARIOS[state.scenario_name]['steps']
        step = steps[state.step_name]
        handler = getattr(handlers, step['handler'])
        if handler(text=text, context=state.context):
            # next step
            next_step = steps[step['next_step']]
            text_to_send = next_step['text'].format(**state.context)
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
        return text_to_send


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    configure_logging()
    bot = Bot(group_id=settings.GROUP_ID, token=settings.TOKEN)
    bot.run()
