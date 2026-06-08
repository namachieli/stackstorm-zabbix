import mock

from zabbix_base_action_test_case import ZabbixBaseActionTestCase
from find_object import FindObject

from zabbix_utils.exceptions import APIRequestError


class FindObjectTestCase(ZabbixBaseActionTestCase):
    __test__ = True
    action_cls = FindObject

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_find_single_host(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.host.get.return_value = [{'hostid': '10084'}]

        result = action.run(
            object_type='host', filter_field='host',
            id_field='hostid', name='myhost')
        self.assertEqual(result, '10084')
        action.client.host.get.assert_called_with(filter={'host': 'myhost'})

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_find_host_not_found(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.host.get.return_value = []

        with self.assertRaises(ValueError):
            action.run(
                object_type='host', filter_field='host',
                id_field='hostid', name='nonexistent')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_find_host_multiple_found(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.host.get.return_value = [
            {'hostid': '1'}, {'hostid': '2'}]

        with self.assertRaises(ValueError):
            action.run(
                object_type='host', filter_field='host',
                id_field='hostid', name='duplicate')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_find_multiple_hosts(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.host.get.return_value = [
            {'hostid': '1'}, {'hostid': '2'}]

        result = action.run(
            object_type='host', filter_field='host',
            id_field='hostid', name=['h1', 'h2'], allow_multiple=True)
        self.assertEqual(result, ['1', '2'])

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_find_multiple_empty(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.host.get.return_value = []

        result = action.run(
            object_type='host', filter_field='host',
            id_field='hostid', name=['nonexistent'], allow_multiple=True)
        self.assertEqual(result, [])

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_find_hostgroup(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.hostgroup.get.return_value = [{'groupid': '5'}]

        result = action.run(
            object_type='hostgroup', filter_field='name',
            id_field='groupid', name='Linux servers')
        self.assertEqual(result, '5')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_find_template(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.template.get.return_value = [{'templateid': '100'}]

        result = action.run(
            object_type='template', filter_field='host',
            id_field='templateid', name='Template OS Linux')
        self.assertEqual(result, '100')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_find_invalid_object_type(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock(spec=[])

        with self.assertRaises(ValueError):
            action.run(
                object_type='invalid', filter_field='name',
                id_field='id', name='test')

    @mock.patch('lib.actions.ZabbixBaseAction.connect')
    def test_find_api_error(self, mock_connect):
        action = self.get_action_instance(self.full_config)
        action.client = mock.Mock()
        action.client.host.get.side_effect = APIRequestError('API error')

        with self.assertRaises(APIRequestError):
            action.run(
                object_type='host', filter_field='host',
                id_field='hostid', name='test')
