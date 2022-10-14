from sqlite3 import Timestamp
from common_types_and_consts import *
from data_access_layer import get_results

class Event:
    command_called_at: str
    command_finished_at: str
    slack_handle: str
    command: str
    result: str

class Logger:
    def __new__(cls, *args, **kwargs):
        if cls is Logger:
            raise TypeError(f"only children of '{cls.__name__}' may be instantiated")
        return object.__new__(cls, *args, **kwargs)

    @staticmethod
    def log_event(event: Event):
        query = config['insert-log'].replace('@@command_called_at@@', event.command_called_at)\
            .replace('@@command_finished_at@@', event.command_finished_at)\
            .replace('@@command@@', event.command)\
            .replace('@@slack_handle@@', event.slack_handle)\
            .replace('@@result@@', event.result)
        get_results(config['pg-bot-db-conn-str'], query)