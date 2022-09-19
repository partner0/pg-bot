from enum import Enum

VERSION_MESSAGE = 'pg-bot API v0.0.9'
ACK_MESSAGE = 'Thank you for your request; I am processing your payload. I will post the results here as soon as they are ready.'
REGEX_URL = '^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$'

class format(Enum):
    DICT = 1
    PRETTYTABLE = 2

class errors(Enum):
    MISSING_ELEMENT_FROM_SLACK = {'code': 1, 'message': 'Missing element {} from Slack payload'}
    MALFORMED_RESPONSE_URL = {'code': 2, 'message': 'Malformed "response_rul" from Slack payload'}
    COMMAND_NOT_FOUND = {'code': 3, 'message': 'Command {} not found'}

config = {
    'help-file': 'help.txt',
    'pg-bot-db-conn-str': 'host=10.6.0.3 user=francois password=mHqr7ut9 dbname=pg_bot',
    'get-conn-str-query': 'select hst_conn_str from hst_host where hst_id = @@host_id@@',
    'commands': {
        'list-reports': 'select rpt_name as name, left(rpt_description, 100) as description, hst_name, rpt_default_db_name, rpt_default_report_params from rpt_report join hst_host on rpt_hst_id__default_report_host = hst_id',
        'list-hosts': 'select hst_id, hst_name as name, left(hst_description, 100) as description from hst_host',
        'fetch': 'select * from rpt_report join hst_host on rpt_hst_id__default_report_host = hst_id where rpt_name = \'@@report_name@@\''
    }
}
