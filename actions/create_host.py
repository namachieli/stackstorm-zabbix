from lib.actions import ZabbixBaseAction


class CreateHost(ZabbixBaseAction):
    """Create a new Zabbix host with interface configuration."""

    def _build_interface(self, ipaddr='', domain='', port="10050", is_main=False):
        return {
            "type": 1,
            "main": 1 if is_main else 0,
            "useip": 1 if ipaddr else 0,
            "dns": domain,
            "ip": ipaddr,
            "port": port,
        }

    def _build_interfaces(self, ipaddrs, domains, main_if):
        interfaces = (
            [self._build_interface(ipaddr=x, is_main=(x == main_if)) for x in ipaddrs] +
            [self._build_interface(domain=x, is_main=(x == main_if)) for x in domains]
        )
        return interfaces

    def _assign_proxy(self, proxy_name, new_host_ids):
        proxies = self.client.proxy.get(filter={'host': proxy_name})
        if not proxies:
            raise ValueError("Proxy not found: {0}".format(proxy_name))

        proxy = proxies[0]
        current_hosts = [
            x['hostid'] for x in
            self.client.host.get(proxyids=[proxy['proxyid']])
        ]
        self.client.proxy.update(
            proxyid=proxy['proxyid'],
            hosts=current_hosts + new_host_ids,
        )

    def run(self, name, groups, ipaddrs=None, domains=None, proxy_host=None, main_if=''):
        """Create a Zabbix host.

        Args:
            name: Hostname to create.
            groups: List of host group names to assign.
            ipaddrs: List of IP addresses for interfaces.
            domains: List of DNS names for interfaces.
            proxy_host: Optional proxy name to assign host to.
            main_if: IP or DNS to designate as main interface.
        """
        self.connect()

        if ipaddrs is None:
            ipaddrs = []
        if domains is None:
            domains = []

        hostgroups = [x['groupid'] for x in self.client.hostgroup.get(filter={'name': groups})]

        interfaces = self._build_interfaces(ipaddrs, domains, main_if)

        if not interfaces:
            raise ValueError("At least one IP address or domain is required.")

        # Ensure exactly one main interface exists
        if not any(x['main'] > 0 for x in interfaces):
            interfaces[0]['main'] = 1

        new_host = self.client.host.create(
            host=name,
            groups=[{'groupid': x} for x in hostgroups],
            interfaces=interfaces,
        )

        if proxy_host:
            self._assign_proxy(proxy_host, new_host['hostids'])

        return new_host
