#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import random

import six

from rally.common.i18n import _, _LE
from rally.common import log as logging
from rally import consts
from rally import exceptions
from rally import osclients
from rally.task import context

LOG = logging.getLogger(__name__)


@context.configure(name="api_versions", order=150)
class OpenStackAPIVersions(context.Context):
    """Context for specifying OpenStack clients versions and service types."""

    CONFIG_SCHEMA = {
        "type": "object",
        "$schema": consts.JSON_SCHEMA,
        "patternProperties": {
            "^[a-z]+$": {
                "type": "object",
                "properties": {
                    "version": {
                        "anyOf": [{"type": "string"}, {"type": "number"}]
                    },
                    "service_name": {
                        "type": "string"
                    },
                    "service_type": {
                        "type": "string"
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }

    def setup(self):
        # FIXME(andreykurilin): move all checks to validate method.

        # do not use admin, if we have users...
        user = random.choice(self.context.get("users",
                                              [self.context["admin"]]))
        clients = osclients.Clients(user["endpoint"])
        services = clients.services()
        for client_name, conf in six.iteritems(self.config):
            if "service_type" in conf and conf["service_type"] not in services:
                raise exceptions.ValidationError(_(
                    "There is no service with '%s' type in your environment.")
                    % conf["service_type"])
            elif "service_name" in conf:
                if conf["service_name"] not in services.values():
                    raise exceptions.ValidationError(
                        _("There is no '%s' service in your environment") %
                        conf["service_name"])

                service_types = [
                    key for key in services
                    if services[key] == conf["service_name"]]

                if len(service_types) > 1:
                    # NOTE(andreykurilin): does it possible??
                    raise exceptions.ValidationError(
                        _("There are several services with name '%s'. Try to "
                          "specify service_type property instead.") %
                        conf["service_name"])
                self.context["config"]["api_versions"][client_name][
                    "service_type"] = service_types[0]

    def cleanup(self):
        # nothing to do here
        pass

    @classmethod
    def validate(cls, config, non_hidden=False):
        super(OpenStackAPIVersions, cls).validate(config,
                                                  non_hidden=non_hidden)
        for client in config:
            client_cls = osclients.OSClient.get(client)
            if ("service_type" in config[client] and
                    "service_name" in config[client]):
                raise exceptions.ValidationError(_LE(
                    "Setting both 'service_type' and 'service_name' properties"
                    " is restricted."))
            try:
                if ("service_type" in config[client] or
                        "service_name" in config[client]):
                    client_cls.is_service_type_configurable()

                if "version" in config[client]:
                    client_cls.validate_version(config[client]["version"])

            except exceptions.RallyException as e:
                raise exceptions.ValidationError(
                    _LE("Invalid settings for '%(client)s': %(error)s") % {
                        "client": client,
                        "error": e.format_message()})
