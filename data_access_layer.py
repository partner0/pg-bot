from common_types_and_consts import *
import psycopg2
import prettytable

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
    conn.commit()
    conn.close()
    return result
