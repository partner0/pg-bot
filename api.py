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

@app.post("/help")
@app.get("/help")
async def help(request: Request, response: Response):
    with open(config['help-file']) as help_file:
        help_content = help_file.read()
        help_file.close()
    return '```' + help_content + '```'

@app.post("/list/{type}")
@app.get("/list/{type}")
async def list(type: str, request: Request, response: Response):
    match type:
        case 'reports':
            result = '```' + (get_results(config['pg-bot-db-conn-str'], config['commands']['list-reports'])).get_string() + '```'
        case 'hosts':
            result = '```' + (get_results(config['pg-bot-db-conn-str'], config['commands']['list-hosts'])).get_string() + '```'
        case default:
            response.status_code = status.HTTP_404_NOT_FOUND
            result = errors.COMMAND_NOT_FOUND
    return result

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
        json = re.findall(r'{.*}', params['text'])
        if json:
            json = json[0]
            slack_command_params = params['text'].replace(json, '').strip().split(' ')
            slack_command_params.append(json)
        else:
            slack_command_params = params['text'].strip().split(' ')
    if not 'response_url'in params:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error = errors.MISSING_ELEMENT_FROM_SLACK
        error.value['message'] = error.value['message'].format('response_url')
        return error
    if not re.match(REGEX_URL, params['response_url']):
        return errors.MALFORMED_RESPONSE_URL 
    if slack_command_params == []:
        return await root(request, response)
    if len (slack_command_params) == 1:
            if not globals()[slack_command_params[0]]:
                response.status_code = status.HTTP_404_NOT_FOUND
                error = errors.COMMAND_NOT_FOUND
                error.value['message'] = error.value['message'].format(slack_command_params[0])
                return error
            return await globals()[slack_command_params[0]](request, response)
    match slack_command_params[0]:
        case 'list':
            return await list(slack_command_params[1], request, response)
        case 'fetch' | 'async_test':
            background_tasks.add_task(process_slack_command, params, slack_command_params)
            return ACK_MESSAGE
        case default:
            response.status_code = status.HTTP_404_NOT_FOUND
            error = errors.COMMAND_NOT_FOUND
            error.value['message'] = error.value['message'].format(slack_command_params[0])
            return error
