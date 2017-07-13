# Copyright 2017 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock

from mistral_lib import actions

from tripleo_common.actions import derive_params
from tripleo_common.tests import base


class GetDpdkNicsNumaInfoActionTest(base.TestCase):

    def test_run_dpdk_port(self):
        network_configs = [{
            "members": [{
                "members": [{"name": "nic5", "type": "interface"}],
                "name": "dpdk0",
                "type": "ovs_dpdk_port",
                "mtu": 8192,
                "rx_queue": 4}],
            "name": "br-link",
            "type": "ovs_user_bridge"}]

        inspect_data = {
            "numa_topology": {
                "nics": [{"name": "ens802f1", "numa_node": 1},
                         {"name": "ens802f0", "numa_node": 1},
                         {"name": "eno1", "numa_node": 0},
                         {"name": "eno2", "numa_node": 0},
                         {"name": "enp12s0f1", "numa_node": 0},
                         {"name": "enp12s0f0", "numa_node": 0},
                         {"name": "enp13s0f0", "numa_node": 0},
                         {"name": "enp13s0f1", "numa_node": 0}]
                },
            "inventory": {
                "interfaces": [{"has_carrier": True,
                                "name": "ens802f1"},
                               {"has_carrier": True,
                                "name": "ens802f0"},
                               {"has_carrier": True,
                                "name": "eno1"},
                               {"has_carrier": True,
                                "name": "eno2"},
                               {"has_carrier": True,
                                "name": "enp12s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f1"}]
                }
            }

        expected_result = [{'name': 'ens802f1', 'mtu': 8192, 'numa_node': 1}]

        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkNicsNumaInfoAction(network_configs,
                                                         inspect_data)
        result = action.run(mock_ctx)
        self.assertEqual(result, expected_result)

    def test_run_dpdk_bond(self):
        network_configs = [{
            "members": [{"type": "ovs_dpdk_bond", "name": "dpdkbond0",
                         "mtu": 9000, "rx_queue": 4,
                         "members": [{"type": "ovs_dpdk_port",
                                      "name": "dpdk0",
                                      "members": [{"type": "interface",
                                                   "name": "nic4"}]},
                                     {"type": "ovs_dpdk_port",
                                      "name": "dpdk1",
                                      "members": [{"type": "interface",
                                                   "name": "nic5"}]}]}],
            "name": "br-link",
            "type": "ovs_user_bridge"}]
        inspect_data = {
            "numa_topology": {
                "nics": [{"name": "ens802f1", "numa_node": 1},
                         {"name": "ens802f0", "numa_node": 1},
                         {"name": "eno1", "numa_node": 0},
                         {"name": "eno2", "numa_node": 0},
                         {"name": "enp12s0f1", "numa_node": 0},
                         {"name": "enp12s0f0", "numa_node": 0},
                         {"name": "enp13s0f0", "numa_node": 0},
                         {"name": "enp13s0f1", "numa_node": 0}]
                },
            "inventory": {
                "interfaces": [{"has_carrier": True,
                                "name": "ens802f1"},
                               {"has_carrier": True,
                                "name": "ens802f0"},
                               {"has_carrier": True,
                                "name": "eno1"},
                               {"has_carrier": True,
                                "name": "eno2"},
                               {"has_carrier": True,
                                "name": "enp12s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f1"}]
                }
            }
        expected_result = [{'mtu': 9000, 'numa_node': 1, 'name': 'ens802f0'},
                           {'mtu': 9000, 'numa_node': 1, 'name': 'ens802f1'}]

        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkNicsNumaInfoAction(network_configs,
                                                         inspect_data)
        result = action.run(mock_ctx)
        self.assertEqual(result, expected_result)

    @mock.patch.object(actions, 'Result', autospec=True)
    def test_run_no_inspect_nics(self, mock_actions):

        network_configs = [{
            "members": [{
                "members": [{"name": "nic5", "type": "interface"}],
                "name": "dpdk0",
                "type": "ovs_dpdk_port",
                "mtu": 8192,
                "rx_queue": 4}],
            "name": "br-link",
            "type": "ovs_user_bridge"}]

        inspect_data = {
            "numa_topology": {
                "nics": []
                },
            "inventory": {
                "interfaces": [{"has_carrier": True,
                                "name": "ens802f1"},
                               {"has_carrier": True,
                                "name": "ens802f0"},
                               {"has_carrier": True,
                                "name": "eno1"},
                               {"has_carrier": True,
                                "name": "eno2"},
                               {"has_carrier": True,
                                "name": "enp12s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f1"}]
                }
            }

        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkNicsNumaInfoAction(network_configs,
                                                         inspect_data)
        action.run(mock_ctx)
        msg = 'Introspection data does not have numa_topology.nics'
        mock_actions.assert_called_once_with(error=msg)

    @mock.patch.object(actions, 'Result', autospec=True)
    def test_run_no_inspect_interfaces(self, mock_actions):

        network_configs = [{
            "members": [{
                "members": [{"name": "nic5", "type": "interface"}],
                "name": "dpdk0",
                "type": "ovs_dpdk_port",
                "mtu": 8192,
                "rx_queue": 4}],
            "name": "br-link",
            "type": "ovs_user_bridge"}]

        inspect_data = {
            "numa_topology": {
                "nics": []
                },
            "inventory": {
                "interfaces": []
                }
            }

        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkNicsNumaInfoAction(network_configs,
                                                         inspect_data)
        action.run(mock_ctx)
        msg = 'Introspection data does not have inventory.interfaces'
        mock_actions.assert_called_once_with(error=msg)

    @mock.patch.object(actions, 'Result', autospec=True)
    def test_run_no_inspect_active_interfaces(self, mock_actions):

        network_configs = [{
            "members": [{
                "members": [{"name": "nic5", "type": "interface"}],
                "name": "dpdk0",
                "type": "ovs_dpdk_port",
                "mtu": 8192,
                "rx_queue": 4}],
            "name": "br-link",
            "type": "ovs_user_bridge"}]

        inspect_data = {
            "numa_topology": {
                "nics": [{"name": "ens802f1", "numa_node": 1},
                         {"name": "ens802f0", "numa_node": 1},
                         {"name": "eno1", "numa_node": 0},
                         {"name": "eno2", "numa_node": 0},
                         {"name": "enp12s0f1", "numa_node": 0},
                         {"name": "enp12s0f0", "numa_node": 0},
                         {"name": "enp13s0f0", "numa_node": 0},
                         {"name": "enp13s0f1", "numa_node": 0}]
                },
            "inventory": {
                "interfaces": [{"has_carrier": False,
                                "name": "enp13s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f1"}]
                }
            }

        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkNicsNumaInfoAction(network_configs,
                                                         inspect_data)
        action.run(mock_ctx)
        msg = 'Unable to determine active interfaces (has_carrier)'
        mock_actions.assert_called_once_with(error=msg)

    @mock.patch.object(actions, 'Result', autospec=True)
    def test_run_no_numa_node(self, mock_actions):
        network_configs = [{
            "members": [{
                "members": [{"name": "nic5", "type": "interface"}],
                "name": "dpdk0",
                "type": "ovs_dpdk_port",
                "mtu": 8192,
                "rx_queue": 4}],
            "name": "br-link",
            "type": "ovs_user_bridge"}]

        inspect_data = {
            "numa_topology": {
                "nics": [{"name": "ens802f1"},
                         {"name": "ens802f0", "numa_node": 1},
                         {"name": "eno1", "numa_node": 0},
                         {"name": "eno2", "numa_node": 0},
                         {"name": "enp12s0f1", "numa_node": 0},
                         {"name": "enp12s0f0", "numa_node": 0},
                         {"name": "enp13s0f0", "numa_node": 0},
                         {"name": "enp13s0f1", "numa_node": 0}]
                },
            "inventory": {
                "interfaces": [{"has_carrier": True,
                                "name": "ens802f1"},
                               {"has_carrier": True,
                                "name": "ens802f0"},
                               {"has_carrier": True,
                                "name": "eno1"},
                               {"has_carrier": True,
                                "name": "eno2"},
                               {"has_carrier": True,
                                "name": "enp12s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f0"},
                               {"has_carrier": False,
                                "name": "enp13s0f1"}]
                }
            }

        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkNicsNumaInfoAction(network_configs,
                                                         inspect_data)
        action.run(mock_ctx)
        msg = 'Unable to determine NUMA node for DPDK NIC: ens802f1'
        mock_actions.assert_called_once_with(error=msg)


class GetDpdkCoreListActionTest(base.TestCase):

    def test_run(self):
        inspect_data = {
            "numa_topology": {
                "cpus": [{"cpu": 21, "numa_node": 1,
                          "thread_siblings": [38, 82]},
                         {"cpu": 27, "numa_node": 0,
                          "thread_siblings": [20, 64]},
                         {"cpu": 3, "numa_node": 1,
                          "thread_siblings": [25, 69]},
                         {"cpu": 20, "numa_node": 0,
                          "thread_siblings": [15, 59]},
                         {"cpu": 17, "numa_node": 1,
                          "thread_siblings": [34, 78]},
                         {"cpu": 16, "numa_node": 0,
                          "thread_siblings": [11, 55]}]
                }
            }

        numa_nodes_cores_count = [2, 1]

        expected_result = "20,64,15,59,38,82"

        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkCoreListAction(inspect_data,
                                                     numa_nodes_cores_count)
        result = action.run(mock_ctx)
        self.assertEqual(result, expected_result)

    @mock.patch.object(actions, 'Result', autospec=True)
    def test_run_invalid_inspect_data(self, mock_actions):
        inspect_data = {"numa_topology": {"cpus": []}}

        numa_nodes_cores_count = [2, 1]

        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkCoreListAction(inspect_data,
                                                     numa_nodes_cores_count)
        action.run(mock_ctx)
        msg = 'Introspection data does not have numa_topology.cpus'
        mock_actions.assert_called_once_with(error=msg)

    @mock.patch.object(actions, 'Result', autospec=True)
    def test_run_invalid_numa_nodes_cores_count(self, mock_actions):
        inspect_data = {"numa_topology": {
            "cpus": [{"cpu": 21, "numa_node": 1, "thread_siblings": [38, 82]},
                     {"cpu": 27, "numa_node": 0, "thread_siblings": [20, 64]}]
            }}

        numa_nodes_cores_count = []

        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkCoreListAction(inspect_data,
                                                     numa_nodes_cores_count)
        action.run(mock_ctx)
        msg = 'CPU physical cores count for each NUMA nodes is not available'
        mock_actions.assert_called_once_with(error=msg)


class GetHostCpusListActionTest(base.TestCase):

    def test_run_valid_inspect_data(self):
        inspect_data = {
            "numa_topology": {
                "cpus": [{"cpu": 21, "numa_node": 1,
                          "thread_siblings": [38, 82]},
                         {"cpu": 27, "numa_node": 0,
                          "thread_siblings": [20, 64]},
                         {"cpu": 3, "numa_node": 1,
                          "thread_siblings": [25, 69]},
                         {"cpu": 20, "numa_node": 0,
                          "thread_siblings": [15, 59]}]
                }
            }
        expected_result = "15,59,25,69"

        mock_ctx = mock.MagicMock()
        action = derive_params.GetHostCpusListAction(inspect_data)
        result = action.run(mock_ctx)
        self.assertEqual(result, expected_result)

    @mock.patch.object(actions, 'Result', autospec=True)
    def test_run_invalid_inspect_data(self, mock_actions):
        inspect_data = {"numa_topology": {"cpus": []}}

        mock_ctx = mock.MagicMock()
        action = derive_params.GetHostCpusListAction(inspect_data)
        action.run(mock_ctx)
        msg = 'Introspection data does not have numa_topology.cpus'
        mock_actions.assert_called_once_with(error=msg)


class GetDpdkSocketMemoryActionTest(base.TestCase):

    def test_run_valid_dpdk_nics_numa_info(self):
        dpdk_nics_numa_info = [{"name": "ens802f1", "numa_node": 1,
                                "mtu": 8192}]
        numa_nodes = [0, 1]
        overhead = 800
        packet_size_in_buffer = (4096 * 64)

        expected_result = "1024,3072"
        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkSocketMemoryAction(
            dpdk_nics_numa_info, numa_nodes, overhead,
            packet_size_in_buffer)
        result = action.run(mock_ctx)
        self.assertEqual(result, expected_result)

    def test_run_multiple_mtu_in_same_numa_node(self):
        dpdk_nics_numa_info = [{"name": "ens802f1", "numa_node": 1,
                                "mtu": 1500},
                               {"name": "ens802f2", "numa_node": 1,
                                "mtu": 2048}]
        numa_nodes = [0, 1]
        overhead = 800
        packet_size_in_buffer = (4096 * 64)

        expected_result = "1024,2048"
        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkSocketMemoryAction(
            dpdk_nics_numa_info, numa_nodes, overhead, packet_size_in_buffer)
        result = action.run(mock_ctx)
        self.assertEqual(result, expected_result)

    def test_run_duplicate_mtu_in_same_numa_node(self):
        dpdk_nics_numa_info = [{"name": "ens802f1", "numa_node": 1,
                                "mtu": 4096},
                               {"name": "ens802f2", "numa_node": 1,
                                "mtu": 4096}]
        numa_nodes = [0, 1]
        overhead = 800
        packet_size_in_buffer = (4096 * 64)

        expected_result = "1024,2048"
        mock_ctx = mock.MagicMock()
        action = derive_params.GetDpdkSocketMemoryAction(
            dpdk_nics_numa_info, numa_nodes, overhead, packet_size_in_buffer)
        result = action.run(mock_ctx)
        self.assertEqual(result, expected_result)
