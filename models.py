from pony.orm import Database, Required, Json
from settings import DB_CONFIG
from datetime import datetime

db = Database()
db.bind(**DB_CONFIG)


class UserState(db.Entity):
    """User state in scenario"""
    user_id = Required(str, unique=True)
    scenario_name = Required(str)
    step_name = Required(str)
    context = Required(Json)


class Ticket(db.Entity):
    departure_airport = Required(str)
    arrival_airport = Required(str)
    date = Required(datetime)


db.generate_mapping(create_tables=True)
