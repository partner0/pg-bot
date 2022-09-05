from fastapi import FastAPI, Request, BackgroundTasks
from enum import Enum
from pydantic import BaseModel
from urllib import parse
import prettytable
import psycopg2
import httpx

#remove
import time

app = FastAPI()

class format(Enum):
    dict = 1
    prettytable = 2

class slack_request(BaseModel):
    """
    token: str
    team_id: str
    team_domain: str
    channel_id: str
    channel_name: str
    user_id: str
    user_name: str
    command: str
    text: str
    api_app_id: str
    is_enterprise_install: str
    """
    response_url: str
    #trigger_id: str

config = {
    'pg-bot-db-conn-str': 'host=10.6.0.3 user=francois password=mHqr7ut9 dbname=pg_bot',
    'commands': {
        'list': 'select rpt_name as name, left(rpt_description, 100) as description from rpt_report join hst_host on rpt_hst_id__default_report_host = hst_id',
        'fetch': 'select hst_conn_str, rpt_default_db_name, rpt_query, rpt_default_conn_params from rpt_report join hst_host on rpt_hst_id__default_report_host = hst_id where rpt_name = \'@@report_name@@\''
    }
}

url_pattern = "^https?:\\/\\/(?:www\\.)?[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)$"

def get_results(conn_str: str, sql: str, params={}, format: format = format.prettytable):
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute(sql)
    match format:
        case format.prettytable:
            result = prettytable.from_db_cursor(cursor)
            if not result:
                result = prettytable.PrettyTable()
                result.field_names = ["Empty resultset"]
            result.align = "l"
        case format.dict:
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(columns, row)) for row in rows]
        case default:
            result = None
    conn.close()
    return result

async def process_slack_command(params):
    print(time.ctime())
    print('Background task started: process_slack_command')
    print(params)
    print('Sleeping for 2 seconds')
    time.sleep(2)
    print(time.ctime())
    #print('Calling root')
    #with httpx.Client() as client:
    #    response = client.post('https://pg-bot-kc7cm5oemq-uc.a.run.app/', data='')
    #print(time.ctime())
    #print('Root called, response: ' + str(response))
    #print('Sleeping for 2 seconds')
    #time.sleep(2)
    #print(time.ctime())
    print('Calling ' + params['response_url'])
    with httpx.Client() as client:
        response = client.post(params['response_url'], data='{{"text" : "Callback worked"}}', headers={'content-type': 'text/plain'})
    print(time.ctime())
    print(params['response_url'] + ' called, response: ' + str(response))
    return

@app.post("/")
@app.get("/")
async def root():
    return {"status": "OK", "version":"0.0.6"}

@app.post("/echo")
@app.get("/echo")
async def echo(request: Request):
    print('echo called')
    body = await request.body()
    return {
            "method": str(request.method),
            "url": str(request.url),
            "headers": str(request.headers),
            "body": body,
            "client-addr": str(request.client)
        }

@app.post("/slack_command")
@app.get("/slack_command")
async def slack_command(request: Request, background_tasks: BackgroundTasks):
    """
    if not request.response_url or request.response_url == '':
        return {500, 'Missing response_url from get/post data'}
    request.response_url = parse.unquote(request.response_url)
    if not re.match(url_pattern, request.response_url):
        return {500, 'Malformed response_url from get/post data'}
    """
    body = await request.body()
    print(body)
    params = parse.parse_qs(body)
    params = {k.decode(): v[0].decode() for k, v in params.items()}
    background_tasks.add_task(process_slack_command, params)
    return {}

@app.post("/list")
@app.get("/list")
async def list():
    return (get_results(config['pg-bot-db-conn-str'], config['commands']['list'])).get_string()

@app.post("/fetch/{report_name}")
@app.get("/fetch/{report_name}")
async def list(report_name):
    report = (get_results(config['pg-bot-db-conn-str'], config['commands']['fetch'].replace('@@report_name@@', report_name), format=format.dict))[0]
    return (get_results(report['hst_conn_str'] + ' dbname=' + report['rpt_default_db_name'], report['rpt_query'])).get_string()
