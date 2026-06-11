from lib.actions import ZabbixBaseAction
from zabbix_utils.exceptions import APIRequestError


class MaintenanceDelete(ZabbixBaseAction):
    """Delete a Zabbix maintenance window by name or ID."""

    def run(self, maintenance_id=None, maintenance_window_name=None):
        """Delete a maintenance window.

        Args:
            maintenance_id: ID of the maintenance window to delete.
            maintenance_window_name: Name of the maintenance window to delete.
        """
        self.connect()

        if maintenance_window_name is not None:
            maintenance_result = self.maintenance_get(maintenance_window_name)

            if len(maintenance_result) == 0:
                raise ValueError(
                    "Could not find maintenance window: {0}".format(
                        maintenance_window_name))
            elif len(maintenance_result) == 1:
                maintenance_id = maintenance_result[0]['maintenanceid']
            else:
                raise ValueError(
                    "Multiple maintenance windows found: {0}".format(
                        maintenance_window_name))
        elif maintenance_id is None:
            raise ValueError(
                "Must provide either maintenance_window_name or maintenance_id")

        try:
            self.client.maintenance.delete(maintenance_id)
        except APIRequestError as e:
            raise APIRequestError(
                "Failed to delete maintenance window: {0}".format(e))

        return True
