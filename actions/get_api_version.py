from lib.actions import ZabbixBaseAction


class GetApiVersion(ZabbixBaseAction):
    def run(self):
        self.connect()
        version = self.client.api_version()
        return str(version)
