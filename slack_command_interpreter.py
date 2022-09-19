
from common_types_and_consts import config, errors, REGEX_URL
from data_access_layer import get_results
import httpx
import json
from api import *

#remove
import time

async def process_slack_command(params: dict, slack_command_params: list):
    print(str(time.ctime()) + ': Background task started: process_slack_command')
    print(params)
    print(slack_command_params)
    slack_headers = {'content-type': 'text/plain'}
    match slack_command_params[0]:
        case 'fetch':
            reports = get_results(config['pg-bot-db-conn-str'], config['commands']['fetch'].replace('@@report_name@@', slack_command_params[1]), format=format.DICT)
            if len(reports) == 0:
                with httpx.Client() as client:
                    error = errors.COMMAND_NOT_FOUND
                    error.value['message'] = error.value['message'].format(slack_command_params[1])
                    response = client.post(params['response_url'], data = str(error.value), headers = slack_headers)
                return
            query = reports[0]['rpt_query']
            if len(slack_command_params) == 3:
                report_config = json.loads(slack_command_params[2])
            else:
                report_config = {}
            if 'report-params' in report_config:
                report_params = report_config['report-params']
            else:
                report_params = json.loads(reports[0]['rpt_default_report_params'])
            if 'hist-id' in report_config:
                host_id = report_config['host-id']
            else:
                host_id = None
            if 'db-name' in report_config:
                db_name = report_config['db-name']
            else:
                db_name = reports[0]['rpt_default_db_name']
            if host_id:
                host_conn_str = get_results(config['pg-bot-db-conn-str'], config['get-conn-str-query'].replace('@@host_id@@', str(host_id)), format=format.DICT)['hst_conn_str']
            else:
                host_conn_str = reports[0]['hst_conn_str']
            for key in report_params:
                query = query.replace('@@' + key + '@@', report_params[key])
            result = (get_results(host_conn_str + ' dbname=' + db_name, query)).get_string()
        case 'async_test':
            result = 'Test OK'
        case default:
            with httpx.Client() as client:
                error = errors.COMMAND_NOT_FOUND
                error.value['message'] = error.value['message'].format(slack_command_params[0])
                response = client.post(params['response_url'], data =  str(error.value), headers = slack_headers)
                return
    with httpx.Client() as client:
        print(result)
        response = client.post(params['response_url'], data = '{"text": \"```' + result + '```\"}', headers = slack_headers)
    return
