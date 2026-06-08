import mock

from zabbix_base_action_test_case import ZabbixBaseActionTestCase
from host_status import HostStatus

from zabbix_utils.exceptions import ProcessingError
from zabbix_utils.exceptions import APIRequestError


class HostStatusTestCase(ZabbixBaseActionTestCase):
    __test__ = True
    action_cls = HostStatus

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_get_status(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.connect = mock_connect
        action.find_host = mock.MagicMock(return_value='1')
        action.zabbix_host = {'hostid': '1', 'status': '0'}

        result = action.run(hostname='test')
        self.assertEqual(result, '0')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_update_status(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.connect = mock_connect
        action.find_host = mock.MagicMock(return_value='1')
        action.client = mock.Mock()
        action.client.host.update.return_value = {'hostids': ['1']}

        result = action.run(hostname='test', status=1)
        self.assertEqual(result, True)
        action.client.host.update.assert_called_with(hostid='1', status=1)

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_connection_error(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        mock_connect.side_effect = ProcessingError('connection error')

        with self.assertRaises(ProcessingError):
            action.run(hostname='test')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_host_not_found(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.connect = mock_connect
        action.find_host = mock.MagicMock(
            side_effect=ValueError('Could not find host'))

        with self.assertRaises(ValueError):
            action.run(hostname='nonexistent')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_update_status_api_error(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.connect = mock_connect
        action.find_host = mock.MagicMock(return_value='1')
        action.client = mock.Mock()
        action.client.host.update.side_effect = APIRequestError('update failed')

        with self.assertRaises(APIRequestError):
            action.run(hostname='test', status=1)
