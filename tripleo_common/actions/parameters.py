# Copyright 2016 Red Hat, Inc.
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
# Copyright 2106 Red Hat, Inc.
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
import logging
import uuid

from heatclient import exc as heat_exc
from mistral.workflow import utils as mistral_workflow_utils
from swiftclient import exceptions as swiftexceptions

from tripleo_common.actions import base
from tripleo_common.actions import templates
from tripleo_common import constants
from tripleo_common.utils import nodes
from tripleo_common.utils import parameters
from tripleo_common.utils import passwords as password_utils
from tripleo_common.utils import plan as plan_utils

LOG = logging.getLogger(__name__)


class GetParametersAction(templates.ProcessTemplatesAction):
    """Gets list of available heat parameters."""

    def run(self, context):

        cached = self.cache_get(context,
                                self.container,
                                "tripleo.parameters.get")

        if cached is not None:
            return cached

        processed_data = super(GetParametersAction, self).run(context)

        # If we receive a 'Result' instance it is because the parent action
        # had an error.
        if isinstance(processed_data, mistral_workflow_utils.Result):
            return processed_data

        processed_data['show_nested'] = True

        # respect previously user set param values
        swift = self.get_object_client(context)
        heat = self.get_orchestration_client(context)

        try:
            env = plan_utils.get_env(swift, self.container)
        except swiftexceptions.ClientException as err:
            err_msg = ("Error retrieving environment for plan %s: %s" % (
                self.container, err))
            LOG.exception(err_msg)
            return mistral_workflow_utils.Result(error=err_msg)

        params = env.get('parameter_defaults')

        fields = {
            'template': processed_data['template'],
            'files': processed_data['files'],
            'environment': processed_data['environment'],
            'show_nested': True
        }

        result = {
            'heat_resource_tree': heat.stacks.validate(**fields),
            'environment_parameters': params,
        }
        self.cache_set(context,
                       self.container,
                       "tripleo.parameters.get",
                       result)
        return result


class ResetParametersAction(base.TripleOAction):
    """Provides method to delete user set parameters."""

    def __init__(self, container=constants.DEFAULT_CONTAINER_NAME):
        super(ResetParametersAction, self).__init__()
        self.container = container

    def run(self, context):
        swift = self.get_object_client(context)

        try:
            env = plan_utils.get_env(swift, self.container)
        except swiftexceptions.ClientException as err:
            err_msg = ("Error retrieving environment for plan %s: %s" % (
                self.container, err))
            LOG.exception(err_msg)
            return mistral_workflow_utils.Result(error=err_msg)

        try:
            plan_utils.update_in_env(swift, env, 'parameter_defaults',
                                     delete_key=True)
        except swiftexceptions.ClientException as err:
            err_msg = ("Error updating environment for plan %s: %s" % (
                self.container, err))
            LOG.exception(err_msg)
            return mistral_workflow_utils.Result(error=err_msg)

        self.cache_delete(context,
                          self.container,
                          "tripleo.parameters.get")
        return env


class UpdateParametersAction(base.TripleOAction):
    """Updates plan environment with parameters."""

    def __init__(self, parameters,
                 container=constants.DEFAULT_CONTAINER_NAME):
        super(UpdateParametersAction, self).__init__()
        self.container = container
        self.parameters = parameters

    def run(self, context):
        swift = self.get_object_client(context)

        try:
            env = plan_utils.get_env(swift, self.container)
        except swiftexceptions.ClientException as err:
            err_msg = ("Error retrieving environment for plan %s: %s" % (
                self.container, err))
            LOG.exception(err_msg)
            return mistral_workflow_utils.Result(error=err_msg)

        try:
            plan_utils.update_in_env(swift, env, 'parameter_defaults',
                                     self.parameters)
        except swiftexceptions.ClientException as err:
            err_msg = ("Error updating environment for plan %s: %s" % (
                self.container, err))
            LOG.exception(err_msg)
            return mistral_workflow_utils.Result(error=err_msg)

        self.cache_delete(context,
                          self.container,
                          "tripleo.parameters.get")
        return env


class UpdateRoleParametersAction(UpdateParametersAction):
    """Updates role related parameters in plan environment ."""

    def __init__(self, role, container=constants.DEFAULT_CONTAINER_NAME):
        super(UpdateRoleParametersAction, self).__init__(parameters=None,
                                                         container=container)
        self.role = role

    def run(self, context):
        baremetal_client = self.get_baremetal_client(context)
        compute_client = self.get_compute_client(context)
        self.parameters = parameters.set_count_and_flavor_params(
            self.role, baremetal_client, compute_client)
        return super(UpdateRoleParametersAction, self).run(context)


class GeneratePasswordsAction(base.TripleOAction):
    """Generates passwords needed for Overcloud deployment

    This method generates passwords and ensures they are stored in the
    plan environment. This method respects previously generated passwords and
    adds new passwords as necessary.
    """

    def __init__(self, container=constants.DEFAULT_CONTAINER_NAME):
        super(GeneratePasswordsAction, self).__init__()
        self.container = container

    def run(self, context):
        heat = self.get_orchestration_client(context)
        swift = self.get_object_client(context)
        mistral = self.get_workflow_client(context)

        try:
            env = plan_utils.get_env(swift, self.container)
        except swiftexceptions.ClientException as err:
            err_msg = ("Error retrieving environment for plan %s: %s" % (
                self.container, err))
            LOG.exception(err_msg)
            return mistral_workflow_utils.Result(error=err_msg)

        try:
            stack_env = heat.stacks.environment(
                stack_id=self.container)
        except heat_exc.HTTPNotFound:
            stack_env = None

        passwords = password_utils.generate_passwords(mistral, stack_env)

        # if passwords don't yet exist in plan environment
        if 'passwords' not in env:
            env['passwords'] = {}

        # ensure all generated passwords are present in plan env,
        # but respect any values previously generated and stored
        for name, password in passwords.items():
            if name not in env['passwords']:
                env['passwords'][name] = password

        try:
            plan_utils.put_env(swift, env)
        except swiftexceptions.ClientException as err:
            err_msg = "Error uploading to container: %s" % err
            LOG.exception(err_msg)
            return mistral_workflow_utils.Result(error=err_msg)

        self.cache_delete(context,
                          self.container,
                          "tripleo.parameters.get")
        return env['passwords']


class GetPasswordsAction(base.TripleOAction):
    """Get passwords from the environment

    This method returns the list passwords which are used for the deployment.
    It will return a merged list of user provided passwords and generated
    passwords, giving priority to the user provided passwords.
    """

    def __init__(self, container=constants.DEFAULT_CONTAINER_NAME):
        super(GetPasswordsAction, self).__init__()
        self.container = container

    def run(self, context):
        swift = self.get_object_client(context)

        try:
            env = plan_utils.get_env(swift, self.container)
        except swiftexceptions.ClientException as err:
            err_msg = ("Error retrieving environment for plan %s: %s" % (
                self.container, err))
            LOG.exception(err_msg)
            return mistral_workflow_utils.Result(error=err_msg)

        parameter_defaults = env.get('parameter_defaults', {})
        passwords = env.get('passwords', {})
        for name in constants.PASSWORD_PARAMETER_NAMES:
            if name in parameter_defaults:
                passwords[name] = parameter_defaults[name]

        return passwords


class GenerateFencingParametersAction(base.TripleOAction):
    """Generates fencing configuration for a deployment.

    :param nodes_json: list of nodes & attributes in json format
    :param os_auth: dictionary of OS client auth data (if using pxe_ssh)
    :param fence_action: action to take when fencing nodes
    :param delay: time to wait before taking fencing action
    :param ipmi_level: IPMI user level to use
    :param ipmi_cipher: IPMI cipher suite to use
    :param ipmi_lanplus: whether to use IPMIv2.0
    """

    def __init__(self, nodes_json, os_auth, fence_action, delay,
                 ipmi_level, ipmi_cipher, ipmi_lanplus):
        super(GenerateFencingParametersAction, self).__init__()
        self.nodes_json = nodes_json
        self.os_auth = os_auth
        self.fence_action = fence_action
        self.delay = delay
        self.ipmi_level = ipmi_level
        self.ipmi_cipher = ipmi_cipher
        self.ipmi_lanplus = ipmi_lanplus

    def run(self, context):
        """Returns the parameters for fencing controller nodes"""
        hostmap = nodes.generate_hostmap(self.get_baremetal_client(context),
                                         self.get_compute_client(context))
        fence_params = {"EnableFencing": True, "FencingConfig": {}}
        devices = []

        for node in self.nodes_json:
            node_data = {}
            params = {}
            if "mac" in node:
                # Not all Ironic drivers present a MAC address, so we only
                # capture it if it's present
                mac_addr = node["mac"][0]
                node_data["host_mac"] = mac_addr

                # If the MAC isn't in the hostmap, this node hasn't been
                # provisioned, so no fencing parameters are necessary
                if mac_addr not in hostmap:
                    continue

            # Build up fencing parameters based on which Ironic driver this
            # node is using
            if node["pm_type"] == "pxe_ssh":
                # Ironic fencing driver
                node_data["agent"] = "fence_ironic"
                if self.fence_action:
                    params["action"] = self.fence_action
                params["auth_url"] = self.os_auth["auth_url"]
                params["login"] = self.os_auth["login"]
                params["passwd"] = self.os_auth["passwd"]
                params["tenant_name"] = self.os_auth["tenant_name"]
                params["pcmk_host_map"] = "%(compute_name)s:%(bm_name)s" % (
                    {"compute_name": hostmap[mac_addr]["compute_name"],
                     "bm_name": hostmap[mac_addr]["baremetal_name"]})
                if self.delay:
                    params["delay"] = self.delay
            elif (node['pm_type'] == 'ipmi' or node["pm_type"].split('_')[1] in
                  ("ipmitool", "ilo", "drac")):
                # IPMI fencing driver
                node_data["agent"] = "fence_ipmilan"
                if self.fence_action:
                    params["action"] = self.fence_action
                params["ipaddr"] = node["pm_addr"]
                params["passwd"] = node["pm_password"]
                params["login"] = node["pm_user"]
                params["pcmk_host_list"] = hostmap[mac_addr]["compute_name"]
                if "pm_port" in node:
                    params["ipport"] = node["pm_port"]
                if self.ipmi_lanplus:
                    params["lanplus"] = self.ipmi_lanplus
                if self.delay:
                    params["delay"] = self.delay
                if self.ipmi_cipher:
                    params["cipher"] = self.ipmi_cipher
                if self.ipmi_level:
                    params["privlvl"] = self.ipmi_level
            else:
                error = ("Unable to generate fencing parameters for %s" %
                         node["pm_type"])
                raise ValueError(error)

            node_data["params"] = params
            devices.append(node_data)

        fence_params["FencingConfig"]["devices"] = devices
        return {"parameter_defaults": fence_params}


class GetFlattenedParametersAction(GetParametersAction):
    """Get the heat stack tree and parameters in flattened structure.

    This method validates the stack of the container and returns the
    parameters and the heat stack tree. The heat stack tree is flattened
    for easy consumption.
    """

    def __init__(self, container=constants.DEFAULT_CONTAINER_NAME):
        super(GetFlattenedParametersAction, self).__init__(container)

    def _processParams(self, flattened, params):
        for item in params:
            if item not in flattened['parameters']:
                param_obj = {}
                for key, value in params.get(item).items():
                    camel_case_key = key[0].lower() + key[1:]
                    param_obj[camel_case_key] = value
                param_obj['name'] = item
                flattened['parameters'][item] = param_obj
        return list(params)

    def _process(self, flattened, name, data):
        key = str(uuid.uuid4())
        value = {}
        value.update({
            'name': name,
            'id': key
        })
        if 'Type' in data:
            value['type'] = data['Type']
        if 'Description' in data:
            value['description'] = data['Description']
        if 'Parameters' in data:
            value['parameters'] = self._processParams(flattened,
                                                      data['Parameters'])
        if 'NestedParameters' in data:
            nested = data['NestedParameters']
            nested_ids = []
            for nested_key in nested.keys():
                nested_data = self._process(flattened, nested_key,
                                            nested.get(nested_key))
                # nested_data will always have one key (and only one)
                nested_ids.append(list(nested_data)[0])

            value['resources'] = nested_ids

        flattened['resources'][key] = value
        return {key: value}

    def run(self, context):
        # process all plan files and create or update a stack
        processed_data = super(GetFlattenedParametersAction, self).run(context)

        # If we receive a 'Result' instance it is because the parent action
        # had an error.
        if isinstance(processed_data, mistral_workflow_utils.Result):
            return processed_data

        if processed_data['heat_resource_tree']:
            flattened = {'resources': {}, 'parameters': {}}
            self._process(flattened, 'Root',
                          processed_data['heat_resource_tree'])
            processed_data['heat_resource_tree'] = flattened

        return processed_data
