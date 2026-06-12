from lib.actions import ZabbixBaseAction
from zabbix_utils.exceptions import APIRequestError


class HostStatus(ZabbixBaseAction):
    """Get or update host monitoring status by hostname."""

    def run(self, hostname, status=None):
        """Get or update host status.

        If status is provided, updates the host status.
        If status is None, returns the current status.

        Args:
            hostname: Name of the Zabbix host.
            status: New status value (0=monitored, 1=unmonitored) or None to get.
        """
        self.connect()

        host_id = self.find_host(hostname)

        if status is not None:
            try:
                self.client.host.update(hostid=host_id, status=status)
                return True
            except APIRequestError as e:
                raise APIRequestError(
                    "Failed to update host status: {0}".format(e))
        else:
            return self.zabbix_host['status']
