import mock

from zabbix_base_action_test_case import ZabbixBaseActionTestCase
from verify_credentials import VerifyCredentials

from zabbix_utils.exceptions import APIRequestError


class VerifyCredentialsTestCase(ZabbixBaseActionTestCase):
    __test__ = True
    action_cls = VerifyCredentials

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        result = action.run()
        self.assertEqual(result, True)

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run_connection_error(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        mock_connect.side_effect = APIRequestError('login error')
        with self.assertRaises(APIRequestError):
            action.run()
