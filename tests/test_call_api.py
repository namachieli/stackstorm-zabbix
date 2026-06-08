import mock

from zabbix_base_action_test_case import ZabbixBaseActionTestCase
from call_api import CallAPI


class CallAPITest(ZabbixBaseActionTestCase):
    __test__ = True
    action_cls = CallAPI

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run_action(self, mock_conn):
        action = self.get_action_instance(self.full_config)

        # This is a mock of calling API 'hoge'
        action.client = mock.Mock()
        action.client.hoge.return_value = 'result'

        # This checks that a method which is specified in the api_method parameter would be called
        self.assertEqual(action.run(api_method='hoge', param='foo'), 'result')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_call_hierarchized_method(self, mock_conn):
        action = self.get_action_instance(self.full_config)

        # Initialize client object that only accepts request to 'foo.bar' method.
        action.client = mock.Mock(spec=['foo'])
        action.client.foo = mock.Mock(spec=['bar'])
        action.client.foo.bar.return_value = 'result'

        # Send request with proper parameter
        self.assertEqual(action.run(api_method='foo.bar', param='hoge'), 'result')

        # Send request with invalid api_method
        with self.assertRaises(RuntimeError):
            action.run(api_method='foo.hoge', param='hoge')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_run_action_with_empty_parameters(self, mock_conn):
        action = self.get_action_instance(self.full_config)

        # This is a mock of calling API 'hoge' to confirm that
        # params with a value of None (p0) are removed prior to execution
        # Should not remove [ '123', False, {}, [], 0 ]
        def side_effect(*args, **kwargs):
            return (args, kwargs)

        action.client = mock.Mock()
        action.client.hoge.side_effect = side_effect

        result = action.run(api_method='hoge',
            **{'p0': None, 'p1': '123', 'p2': False, 'p3': {}, 'p4': [], 'p5': 0})
        self.assertEqual(result, ((),
            {'p1': '123', 'p2': False, 'p3': {}, 'p4': [], 'p5': 0}))
        action.client.hoge.assert_called_with(
            **{'p1': '123', 'p2': False, 'p3': {}, 'p4': [], 'p5': 0})
