import mock

from zabbix_base_action_test_case import ZabbixBaseActionTestCase
from acknowledge_event import AcknowledgeEvent

from zabbix_utils.exceptions import APIRequestError


class AcknowledgeEventTestCase(ZabbixBaseActionTestCase):
    __test__ = True
    action_cls = AcknowledgeEvent

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_acknowledge_with_close(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.event.acknowledge.return_value = {'eventids': ['123']}

        result = action.run(eventid='123', message='Fixed', will_close=True)
        action.client.event.acknowledge.assert_called_with(
            eventids='123', message='Fixed', action=1)
        self.assertEqual(result, {'eventids': ['123']})

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_acknowledge_without_close(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.event.acknowledge.return_value = {'eventids': ['456']}

        result = action.run(eventid='456', message='Acknowledged', will_close=False)
        action.client.event.acknowledge.assert_called_with(
            eventids='456', message='Acknowledged', action=0)
        self.assertEqual(result, {'eventids': ['456']})

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_acknowledge_api_error(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.event.acknowledge.side_effect = APIRequestError('failed')

        with self.assertRaises(APIRequestError):
            action.run(eventid='789', message='test')
