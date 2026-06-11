from lib.actions import ZabbixBaseAction


class GetApiVersion(ZabbixBaseAction):
    """Get the Zabbix API version."""

    def run(self):
        self.connect()
        return str(self.client.api_version())
