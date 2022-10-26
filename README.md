# pg-bot
Slack command interface for managed postgres hosts and queries

pg-bot [list|fetch]

list [hosts|reports]:
    Lists configured hosts or reports
    eg: 
    /pg-bot list hosts
    /pg-bot list reports

fetch [report_name config|None]
    fetches report report_name with the default config, unless the config object is provided

    config:
    {
        "report-params": <dict of str: parameters, see a given report params structure with /pg-bot list reports>,
        "host-id": <int: id of an host from /pg-bot list hosts>,
        "db-name": <str: override the default db name for the report>
    }

    eg: 
    /pg-bot fetch dora-stats
    /pg-bot fetch dora-stats {"report-params": {"from": "now() - interval '30 days'", "to":"now()"}}
    /pg-bot fetch dora-stats {"report-params": {"from": "now() - interval '30 days'", "to":"now()"}, "host-id": 2, "db-name":"concourse"}
