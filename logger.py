from sqlite3 import Timestamp
from common_types_and_consts import *
from data_access_layer import get_results

class Event:
    command_called_at: str
    command_finished_at: str
    slack_handle: str
    command: str
    host_id: int
    result: str

    def __init__(self, command_called_at: str, command_finished_at: str, slack_handle: str, command: str, host_id: int, result: str):
        self.command_called_at = command_called_at
        self.command_finished_at = command_finished_at
        self.slack_handle = slack_handle
        self.command = command
        self.host_id = host_id
        self.result = result
class Logger:
    def __new__(cls, *args, **kwargs):
        if cls is Logger:
            raise TypeError(f"only children of '{cls.__name__}' may be instantiated")
        return object.__new__(cls, *args, **kwargs)

    @staticmethod
    def log_event(event: Event):
        host_id_sql = 'null'
        if event.host_id:
            host_id_sql = str(event.host_id)
        query = config['insert-log'].replace('@@command_called_at@@', event.command_called_at)\
        .replace('@@command_finished_at@@', event.command_finished_at)\
        .replace('@@slack_handle@@', event.slack_handle)\
        .replace('@@command@@', event.command)\
        .replace('@@host_id@@', host_id_sql)\
        .replace('@@result@@', event.result.replace("'", "''"))
        return get_results(config['pg-bot-db-conn-str'], query, format.DICT)