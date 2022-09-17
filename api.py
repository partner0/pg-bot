from fastapi import FastAPI, Request, Response, status, BackgroundTasks
from common_types_and_consts import *
from data_access_layer import get_results
from slack_command_interpreter import process_slack_command
from urllib import parse
import re

app = FastAPI()

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
    if not 'response_url'in params:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error = errors.MISSING_ELEMENT_FROM_SLACK
        print(error)
        error.value['message'] = error.value['message'].format('response_url')
        return error
    if not re.match(REGEX_URL, params['response_url']):
        return errors.MALFORMED_RESPONSE_URL 
    if len(slack_command_params) == 0:
        return await root(request, response)
    elif len(slack_command_params) == 1 and slack_command_params[0] not in ['async_test']:
        if not globals()[slack_command_params[0]]:
            response.status_code = status.HTTP_404_NOT_FOUND
            return errors.COMMAND_NOT_FOUND
        return await globals()[slack_command_params[0]](request, response)
    else:
        background_tasks.add_task(process_slack_command, params, slack_command_params)
        return ACK_MESSAGE