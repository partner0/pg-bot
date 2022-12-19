
from common_types_and_consts import *
from api import *
from logger import *
from data_access_layer import get_results
import httpx, json, time, os, logging

async def slack_command_error_handler(response_url: str, call_time: str, params: dict, slack_command_params: list, error: Exception) -> None:
    try:
        async with httpx.AsyncClient() as client:
            error_text = 'Error processing slack command\n'
            error_text += f'params: {params}\n'
            error_text += f'slack_command_params: {slack_command_params}\n'
            error_text += f'response_url: {response_url}\n'
            error_text += f'Exception: {error}\n'
            print(error_text)
            await client.post(response_url, data = str(SlackJSONResponse(error_text).body), headers = config['slack-headers'])
            event = Event(call_time, str(time.ctime()), params['user_name'], params['command'] + ' ' + params['text'], None, error_text)
            Logger.log_event(event)
    except Exception as exception:
        logging.exception('Exception during exception handling')
    return


async def process_slack_command(params: dict, slack_command_params: list, base_url: str) -> None:
    try:
        call_time = str(time.ctime())
        print(call_time + ': Background task started: process_slack_command')
        print(params)
        print(slack_command_params)
        response_url = base_url + 'echo'
        if params and 'response_url' in params and "OVERRIDE_CALLBACK" not in os.environ:
            response_url = params['response_url'] 
        match slack_command_params[0]:
            case 'fetch':
                reports = get_results(config['pg-bot-db-conn-str'], config['commands']['fetch'].replace('@@report_name@@', slack_command_params[1]), format=format.DICT)
                if len(reports) == 0:
                    with httpx.AsyncClient() as client:
                        print('fetch command not found')
                        error = errors.COMMAND_NOT_FOUND.value['message'].format(slack_command_params[1])
                        await client.post(response_url, data = error, headers = config['slack-headers'])
                        event = Event(call_time, str(time.ctime()), params['user_name'], params['command'] + ' ' + params['text'], host_id, error)
                        Logger.log_event(event)
                    return
                query = reports[0]['rpt_query']
                default_host_id = reports[0]['rpt_hst_id__default_report_host']
                if len(slack_command_params) == 3:
                    report_config = json.loads(slack_command_params[2])
                else:
                    report_config = {}
                if 'report-params' in report_config:
                    report_params = report_config['report-params']
                else:
                    report_params = json.loads(reports[0]['rpt_default_report_params'])
                if 'host-id' in report_config:
                    host_id = report_config['host-id']
                else:
                    host_id = default_host_id
                if 'db-name' in report_config:
                    db_name = report_config['db-name']
                else:
                    db_name = reports[0]['rpt_default_db_name']
                if host_id:
                    host_conn_str = get_results(config['pg-bot-db-conn-str'], config['get-conn-str-query'].replace('@@host_id@@', str(host_id)), format=format.DICT)[0]['hst_conn_str']
                else:
                    host_conn_str = reports[0]['hst_conn_str']
                for key in report_params:
                    query = query.replace('@@' + key + '@@', report_params[key])
                result = (get_results(host_conn_str + ' dbname=' + db_name, query))
            case 'async_test':
                result = 'Test OK'
            case default:
                print('command not found')
                with httpx.AsyncClient() as client:
                    error = errors.COMMAND_NOT_FOUND.value['message'].format(slack_command_params[0])
                    await client.post(response_url, data =  SlackJSONResponse(error).body, headers = config['slack-headers'])
                    event = Event(call_time, str(time.ctime()), params['user_name'], params['command'] + ' ' + params['text'], host_id, error)
                    Logger.log_event(event)
                    return
        async with httpx.AsyncClient() as client:
            print(response_url)
            print(host_conn_str + ' dbname=' + db_name)
            print(query)
            print(result.get_string())
            await client.post(response_url, data = SlackJSONResponse(result.get_string()).body, headers = config['slack-headers'])
            event = Event(call_time, str(time.ctime()), params['user_name'], params['command'] + ' ' + params['text'], host_id, result.get_json_string(default=str))
            Logger.log_event(event)
    except Exception as exception:
        print("calling echo")
        print(response_url)
        await slack_command_error_handler(response_url, call_time, params, slack_command_params, exception)
        logging.exception('Exception during process_slack_command')
    return