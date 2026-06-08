import mock

from zabbix_base_action_test_case import ZabbixBaseActionTestCase
from host_get_id import HostGetID

from zabbix_utils.exceptions import ProcessingError
from zabbix_utils.exceptions import APIRequestError


class HostGetIDTestCase(ZabbixBaseActionTestCase):
    __test__ = True
    action_cls = HostGetID

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run_connection_error(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        mock_connect.side_effect = ProcessingError('connection error')
        test_dict = {'host': "test"}
        host_dict = {'name': "test", 'hostid': '1'}
        action.find_host = mock.MagicMock(return_value=host_dict['hostid'])

        with self.assertRaises(ProcessingError):
            action.run(**test_dict)

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run_host_error(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        mock_connect.return_vaue = "connect return"
        test_dict = {'host': "test"}
        host_dict = {'name': "test", 'hostid': '1'}
        action.find_host = mock.MagicMock(return_value=host_dict['hostid'],
            side_effect=APIRequestError('host error'))
        action.connect = mock_connect
        with self.assertRaises(APIRequestError):
            action.run(**test_dict)

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        mock_connect.return_vaue = "connect return"
        test_dict = {'host': "test"}
        host_dict = {'name': "test", 'hostid': '1'}
        action.connect = mock_connect
        action.find_host = mock.MagicMock(return_value=host_dict['hostid'])

        result = action.run(**test_dict)
        self.assertEqual(result, host_dict['hostid'])
