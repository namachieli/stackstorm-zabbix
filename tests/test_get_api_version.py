import mock

from zabbix_base_action_test_case import ZabbixBaseActionTestCase
from get_api_version import GetApiVersion

from zabbix_utils.exceptions import ProcessingError


class GetApiVersionTestCase(ZabbixBaseActionTestCase):
    __test__ = True
    action_cls = GetApiVersion

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_get_api_version(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.api_version.return_value = '6.0.46'

        result = action.run()
        self.assertEqual(result, '6.0.46')
        action.client.api_version.assert_called_once()

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_get_api_version_connection_error(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        mock_connect.side_effect = ProcessingError('connection error')

        with self.assertRaises(ProcessingError):
            action.run()
