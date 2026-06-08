from lib.actions import ZabbixBaseAction


class CallAPI(ZabbixBaseAction):
    """Generic Zabbix API method dispatcher.

    Handles any Zabbix API call. Supports both keyword-argument methods
    (get, create, update) and positional-argument methods (delete).
    """

    def run(self, api_method, params_list=None, **params):
        self.connect()

        if params_list is not None:
            # Positional-arg methods (e.g. host.delete takes IDs as positional args)
            method = self._resolve_method(self.client, api_method)
            return method(*params_list)

        # Keyword-arg methods (e.g. host.get, host.create, host.update)
        filtered = {k: v for k, v in params.items() if v is not None}
        method = self._resolve_method(self.client, api_method)
        return method(**filtered)

    def _resolve_method(self, client, api_method):
        """Resolve a dotted API method string to a callable."""
        obj = client
        for attr in api_method.split('.'):
            obj = self._get_attr(obj, attr)
        return obj

    def _get_attr(self, parent_object, attribute):
        if not hasattr(parent_object, attribute):
            raise RuntimeError(
                "Zabbix API does not have a '%s' attribute" % attribute)
        return getattr(parent_object, attribute)
