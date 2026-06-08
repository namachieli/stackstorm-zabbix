from lib.actions import ZabbixBaseAction
from zabbix_utils.exceptions import APIRequestError


class AcknowledgeEvent(ZabbixBaseAction):
    """Acknowledge a Zabbix event with optional close action."""

    def run(self, eventid, message, will_close=True):
        """Acknowledge an event.

        Args:
            eventid: Event ID to acknowledge.
            message: Acknowledgement message.
            will_close: If True, also close the problem (action=1).
        """
        self.connect()

        params = {
            'eventids': eventid,
            'message': message,
            'action': 1 if will_close else 0,
        }

        try:
            return self.client.event.acknowledge(**params)
        except APIRequestError as e:
            raise APIRequestError(
                "Failed to acknowledge event {0}: {1}".format(eventid, e))
