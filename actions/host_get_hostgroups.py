# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from lib.actions import ZabbixBaseAction


class HostGetHostGroups(ZabbixBaseAction):

    def run(self, host_id, group_id):
        """ Gets the hostgroups of one or more Zabbix Hosts.
        """
        self.connect()

        hostgroups = self.host_get_extended(host_id, 'selectGroups',
                                            ['hostid', 'groups'])

        # if group ids are passed in we check to see if the host is a part of said groups
        if group_id:
            for group in hostgroups[0]["groups"]:
                if group["groupid"] == group_id:
                    return hostgroups

            return (False, hostgroups)
        # otherwise just return the groups the host is in
        else:
            return hostgroups
