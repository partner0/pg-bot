from fastapi import FastAPI, Request, Response, status, BackgroundTasks
from typing_extensions import Self
from urllib import parse
from enum import Enum
import prettytable
import psycopg2
import httpx
import re

#remove
import time

app = FastAPI()

VERSION_MESSAGE = 'pg-bot API v0.0.8'
ACK_MESSAGE = 'Thank you for your request; I am processing your payload. I will post the results here as soon as they are ready.'
REGEX_URL = "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"

class format(Enum):
    DICT = 1
    PRETTYTABLE = 2

class errors(Enum):
    MISSING_ELEMENT_FROM_SLACK = {'code': 1, 'message': 'Missing element {} from Slack payload'}
    MALFORMED_RESPONSE_URL = {'code': 2, 'message': 'Malformed "response_rul" from Slack payload'}
    COMMAND_NOT_FOUND = {'code': 3, 'message': 'Command {} not found'}

config = {
    'pg-bot-db-conn-str': 'host=10.6.0.3 user=francois password=mHqr7ut9 dbname=pg_bot',
    'commands': {
        'list': 'select rpt_name as name, left(rpt_description, 100) as description from rpt_report join hst_host on rpt_hst_id__default_report_host = hst_id',
        'fetch': 'select hst_conn_str, rpt_default_db_name, rpt_query, rpt_default_conn_params from rpt_report join hst_host on rpt_hst_id__default_report_host = hst_id where rpt_name = \'@@report_name@@\''
    }
}

def get_results(conn_str: str, sql: str, params={}, format: format = format.PRETTYTABLE):
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute(sql)
    match format:
        case format.PRETTYTABLE:
            result = prettytable.from_db_cursor(cursor)
            if not result:
                result = prettytable.PrettyTable()
                result.field_names = ["Empty resultset"]
            result.align = "l"
        case format.DICT:
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
        case default:
            result = None
    conn.close()
    return result

async def process_slack_command(params: dict, slack_command_params: list):
    print(str(time.ctime()) + ': Background task started: process_slack_command')
    print(params)
    slack_headers = {"content-type": "text/plain"}
    if not 'response_url'in params:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error = errors.MISSING_ELEMENT_FROM_SLACK
        error['message'] = error['message'].format('response_url')
        return error
    if not re.match(REGEX_URL, params['response_url']):
        return errors.MALFORMED_RESPONSE_URL
    match slack_command_params[0]:
        case 'fetch':
            reports = get_results(config['pg-bot-db-conn-str'], config['commands']['fetch'].replace('@@report_name@@', slack_command_params[1]), format=format.DICT)
            if len(reports) == 0:
                with httpx.Client() as client:
                    error = errors.COMMAND_NOT_FOUND
                    error['message'] = error['message'].format(slack_command_params[1])
                    response = client.post(params['response_url'], data = error, headers = slack_headers)
            result = (get_results(reports[0]['hst_conn_str'] + ' dbname=' + reports[0]['rpt_default_db_name'], reports[0]['rpt_query'])).get_string()
        case 'list':
            result = await list(None, None)
        case default:
            with httpx.Client() as client:
                error = errors.COMMAND_NOT_FOUND
                error['message'] = error['message'].format(slack_command_params[0])
                response = client.post(params['response_url'], data = error, headers = slack_headers)
                return
    print('calling: ' + params['response_url'])
    print('data: ' + result)
    with httpx.Client() as client:
        response = client.post(params['response_url'], data = result, headers = slack_headers)
    return

@app.post("/")
@app.get("/")
async def root(request: Request, response: Response):
    return VERSION_MESSAGE

@app.post("/echo")
@app.get("/echo")
async def echo(request: Request, response: Response):
    body = await request.body()
    return {
            "method": str(request.method),
            "url": str(request.url),
            "headers": str(request.headers),
            "body": body,
            "client-addr": str(request.client)
        }

@app.post("/list")
@app.get("/list")
async def list(request: Request, response: Response):
    return (get_results(config['pg-bot-db-conn-str'], config['commands']['list'])).get_string()

@app.post("/fetch/{report_name}")
@app.get("/fetch/{report_name}")
async def fetch(report_name: str, request: Request, response: Response):
    report = (get_results(config['pg-bot-db-conn-str'], config['commands']['fetch'].replace('@@report_name@@', report_name), format=format.DICT))[0]
    return (get_results(report['hst_conn_str'] + ' dbname=' + report['rpt_default_db_name'], report['rpt_query'])).get_string()

@app.post("/slack_command")
@app.get("/slack_command")
async def slack_command(background_tasks: BackgroundTasks, request: Request, response: Response):
    body = await request.body()
    params = parse.parse_qs(body)
    params = {k.decode(): v[0].decode() for k, v in params.items()}
    if not 'text' in params:
        slack_command_params = []
    else:
        slack_command_params = params['text'].split(' ')
    if len(slack_command_params) == 0:
        return await root(request, response)
    elif len(slack_command_params) == 1 and slack_command_params[0] not in ['list']:
        if not globals()[slack_command_params[0]]:
            response.status_code = status.HTTP_404_NOT_FOUND
            return errors.COMMAND_NOT_FOUND
        return await globals()[slack_command_params[0]](request, response)
    else:
        background_tasks.add_task(process_slack_command, params, slack_command_params)
        return ACK_MESSAGE