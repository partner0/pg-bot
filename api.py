from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse
from common_types_and_consts import *
from data_access_layer import get_results
from slack_command_interpreter import process_slack_command
from urllib import parse
import re, json

app = FastAPI()

@app.exception_handler(Exception)
async def validation_exception_handler(request, err):
    base_error_message = f"Failed to execute: {request.method}: {request.url}"
    return SlackJSONResponse(response_text = f"{base_error_message}\ndetails: {err}")

@app.post("/", response_class = JSONResponse)
@app.get("/", response_class = JSONResponse)
async def root(request: Request, response: Response):
    return SlackJSONResponse(VERSION_MESSAGE)

@app.post("/echo", response_class = JSONResponse)
@app.get("/echo", response_class = JSONResponse)
async def echo(request: Request, response: Response):
    request_body = await request.body()
    try:
        response_body = json.loads(request_body)
    except:
        response_body = request_body.decode("utf-8")
    response_body = {
            "method": str(request.method),
            "url": str(request.url),
            "headers": str(request.headers),
            "body": response_body,
            "client-addr": str(request.client)
        }
    response_body = json.dumps(response_body, indent = 4)
    print(response_body)
    return SlackJSONResponse(response_body)

@app.post("/help", response_class = JSONResponse)
@app.get("/help", response_class = JSONResponse)
async def help(request: Request, response: Response):
    with open(config['help-file']) as help_file:
        help_content = help_file.read()
        help_file.close()
    return SlackJSONResponse(help_content)

@app.post("/list/{type}", response_class = JSONResponse)
@app.get("/list/{type}", response_class = JSONResponse)
async def list(type: str, request: Request, response: Response):
    match type:
        case 'reports':
            result = (get_results(config['pg-bot-db-conn-str'], config['commands']['list-reports'])).get_string()
        case 'hosts':
            result = (get_results(config['pg-bot-db-conn-str'], config['commands']['list-hosts'])).get_string()
        case default:
            result = errors.COMMAND_NOT_FOUND.value['message'].format(type)
    return SlackJSONResponse(result)

@app.post("/fetch/{report_name}", response_class = JSONResponse)
@app.get("/fetch/{report_name}", response_class = JSONResponse)
async def fetch(report_name: str, request: Request, response: Response):
    report = (get_results(config['pg-bot-db-conn-str'], config['commands']['fetch'].replace('@@report_name@@', report_name), format=format.DICT))[0]
    return SlackJSONResponse((get_results(report['hst_conn_str'] + ' dbname=' + report['rpt_default_db_name'], report['rpt_query'])).get_string())

@app.post("/slack_command", response_class = JSONResponse)
@app.get("/slack_command", response_class = JSONResponse)
async def slack_command(background_tasks: BackgroundTasks, request: Request, response: Response):
    body = await request.body()
    params = parse.parse_qs(body)
    params = { k.decode(): v[0].decode() for k, v in params.items() }
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
        result = errors.MISSING_ELEMENT_FROM_SLACK.value['message'].format('response_url')
    if not re.match(REGEX_URL, params['response_url']):
        result = errors.MALFORMED_RESPONSE_URL.value['message']
    if slack_command_params == []:
        return await root(request, response)
    if len (slack_command_params) == 1:
        if not globals()[slack_command_params[0]]:
            result = errors.COMMAND_NOT_FOUND.value['message'].format(slack_command_params[0])
        else:
            return await globals()[slack_command_params[0]](request, response)
    match slack_command_params[0]:
        case 'list':
            return await list(slack_command_params[1], request, response)
        case 'fetch' | 'async_test':
            background_tasks.add_task(process_slack_command, params, slack_command_params, str(request.base_url))
            result = ACK_MESSAGE
        case default:
            result = errors.COMMAND_NOT_FOUND.value['message'].format(slack_command_params[0])
    return SlackJSONResponse(result)
