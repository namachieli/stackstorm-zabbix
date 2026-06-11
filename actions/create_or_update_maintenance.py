from datetime import datetime
from tzlocal import get_localzone
from lib.actions import ZabbixBaseAction


class MaintenanceCreateOrUpdate(ZabbixBaseAction):
    """Create or update a Zabbix maintenance window."""

    def run(self, hostname, maintenance_window_name, start_date, end_date,
            time_type=0, maintenance_type=0):
        """Create or update a maintenance window.

        Args:
            hostname: Name of the Zabbix host.
            maintenance_window_name: Name for the maintenance window.
            start_date: Start datetime string (Y-m-d H:M).
            end_date: End datetime string (Y-m-d H:M).
            time_type: Period type (0=one time, 2=daily, 3=weekly, 4=monthly).
            maintenance_type: 0=with data collection, 1=without.
        """
        self.connect()

        host_id = self.find_host(hostname)

        local_tz = get_localzone()

        start_local = datetime.strptime(start_date, "%Y-%m-%d %H:%M")
        start_local = start_local.replace(tzinfo=local_tz)
        start_time = int(start_local.timestamp())

        end_local = datetime.strptime(end_date, "%Y-%m-%d %H:%M")
        end_local = end_local.replace(tzinfo=local_tz)
        end_time = int(end_local.timestamp())

        period = end_time - start_time

        time_period = [{
            'start_date': start_time,
            'timeperiod_type': time_type,
            'period': period,
        }]

        maintenance_params = {
            'hosts': [{'hostid': host_id}],
            'name': maintenance_window_name,
            'active_since': start_time,
            'active_till': end_time,
            'maintenance_type': maintenance_type,
            'timeperiods': time_period,
        }

        result = self.maintenance_create_or_update(maintenance_params)
        return result['maintenanceids'][0]
