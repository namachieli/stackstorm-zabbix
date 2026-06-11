from lib.actions import ZabbixBaseAction
from zabbix_utils.exceptions import APIRequestError


class FindObject(ZabbixBaseAction):
    """Generic name-to-ID resolution for Zabbix objects."""

    def run(self, object_type, filter_field, id_field, name, allow_multiple=False):
        """Resolve a friendly name to an object ID.

        Args:
            object_type: Zabbix API object type (e.g. 'host', 'hostgroup').
            filter_field: Field to filter on (e.g. 'host', 'name').
            id_field: Field containing the ID in results (e.g. 'hostid', 'groupid').
            name: Name value(s) to search for (string or array).
            allow_multiple: If True, return all matching IDs as a list.
        """
        self.connect()

        try:
            api_object = getattr(self.client, object_type)
        except AttributeError:
            raise ValueError("Invalid object type: {0}".format(object_type))

        try:
            results = api_object.get(filter={filter_field: name})
        except APIRequestError as e:
            raise APIRequestError(
                "Error searching for {0}: {1}".format(object_type, e))

        if allow_multiple:
            return [r[id_field] for r in results]

        if len(results) == 0:
            raise ValueError(
                "Could not find {0} with {1}={2}".format(
                    object_type, filter_field, name))
        if len(results) > 1:
            raise ValueError(
                "Multiple {0} found with {1}={2}".format(
                    object_type, filter_field, name))

        return results[0][id_field]
