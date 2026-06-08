from lib.actions import ZabbixBaseAction


class VerifyCredentials(ZabbixBaseAction):
    """Verify Zabbix API connectivity and authentication."""

    def run(self):
        self.connect()
        return True
