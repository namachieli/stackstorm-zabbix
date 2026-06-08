import mock

from zabbix_base_action_test_case import ZabbixBaseActionTestCase
from host_delete import HostDelete

from zabbix_utils.exceptions import ProcessingError
from zabbix_utils.exceptions import APIRequestError


class HostDeleteTestCase(ZabbixBaseActionTestCase):
    __test__ = True
    action_cls = HostDelete

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run_connection_error(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        mock_connect.side_effect = ProcessingError('connection error')
        test_dict = {'hostname': "test"}

        with self.assertRaises(ProcessingError):
            action.run(**test_dict)

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run_host_error(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        mock_connect.return_vaue = "connect return"
        test_dict = {'hostname': "test"}
        action.find_host = mock.MagicMock(
            side_effect=APIRequestError('host error'))
        action.connect = mock_connect

        with self.assertRaises(APIRequestError):
            action.run(**test_dict)

    @mock.patch('lib.actions.ZabbixAPI')
    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run(self, mock_connect, mock_client):
        action = self.get_action_instance(self.full_config)
        mock_connect.return_vaue = "connect return"
        test_dict = {'hostname': "test"}
        host_dict = {'name': "test", 'hostid': '1'}
        action.connect = mock_connect
        action.find_host = mock.MagicMock(return_value=host_dict['hostid'])
        mock_client.host.delete.return_value = "delete return"
        action.client = mock_client

        result = action.run(**test_dict)
        mock_client.host.delete.assert_called_with(host_dict['hostid'])
        self.assertEqual(result, True)

    @mock.patch('lib.actions.ZabbixAPI')
    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run_id(self, mock_connect, mock_client):
        action = self.get_action_instance(self.full_config)
        mock_connect.return_vaue = "connect return"
        test_dict = {'host_id': "1"}
        action.connect = mock_connect
        mock_client.host.delete.return_value = "delete return"
        action.client = mock_client

        result = action.run(**test_dict)
        mock_client.host.delete.assert_called_with(test_dict['host_id'])
        self.assertEqual(result, True)

    @mock.patch('lib.actions.ZabbixAPI')
    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run_delete_error(self, mock_connect, mock_client):
        action = self.get_action_instance(self.full_config)
        mock_connect.return_vaue = "connect return"
        test_dict = {'hostname': "test"}
        host_dict = {'name': "test", 'hostid': '1'}
        action.connect = mock_connect
        action.find_host = mock.MagicMock(return_value=host_dict['hostid'])
        mock_client.host.delete.side_effect = APIRequestError('host error')
        action.client = mock_client

        with self.assertRaises(APIRequestError):
            action.run(**test_dict)

        with self.assertRaises(APIRequestError):
            action.run(**test_dict)
