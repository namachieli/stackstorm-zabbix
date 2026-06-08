from lib.actions import ZabbixBaseAction
from zabbix_utils.exceptions import APIRequestError


class HostDelete(ZabbixBaseAction):
    """Delete a Zabbix host by hostname or ID."""

    def run(self, hostname=None, host_id=None):
        """Delete a host.

        Args:
            hostname: Name of the host to delete (resolved to ID).
            host_id: Direct host ID to delete.
        """
        self.connect()

        if not host_id:
            host_id = self.find_host(hostname)

        try:
            self.client.host.delete(host_id)
            return True
        except APIRequestError as e:
            raise APIRequestError(
                "Failed to delete host: {0}".format(e))
