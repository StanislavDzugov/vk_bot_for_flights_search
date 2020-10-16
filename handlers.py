import re
import time
import datetime

re_name = re.compile(r'\b[A-z]{2,40}\b')
re_date = re.compile(r'\b\d{4}-\d{2}-\d{2}\b')


def handle_name(text, context):
    match = re.match(re_name, text)
    if match:
        context['name'] = text
        return True
    else:
        return False


def handle_date(text, context):
    match = re.match(re_date, text)
    if match:
        user_time = datetime.datetime.strptime(text, '%Y-%m-%d')
        date_now = datetime.datetime.now()
        if user_time.year in range(date_now.year, date_now.year + 2):
            if user_time >= date_now.now() and user_time.year <= 2022:
                context['name'] = text
                return True
            else:
                return False
