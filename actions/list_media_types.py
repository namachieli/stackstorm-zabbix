from lib.actions import ZabbixBaseAction


class ListMediaTypes(ZabbixBaseAction):
    def run(self):
        self.connect()
        result = self.client.mediatype.get(output=["mediatypeid", "name", "type", "status"])
        return result
