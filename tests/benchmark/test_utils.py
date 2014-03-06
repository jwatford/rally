# Copyright 2013: Mirantis Inc.
# All Rights Reserved.
#
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

import mock

from tests import fakes
from tests import test

from rally.benchmark import utils
from rally import exceptions


class BenchmarkUtilsTestCase(test.TestCase):

    def test_resource_is(self):
        is_active = utils.resource_is("ACTIVE")
        self.assertTrue(is_active(fakes.FakeResource(status="active")))
        self.assertTrue(is_active(fakes.FakeResource(status="aCtIvE")))
        self.assertFalse(is_active(fakes.FakeResource(status="ERROR")))

    def test_infinite_run_args(self):
        args = ("a", "b", "c", "d", 123)
        for i, real_args in enumerate(utils.infinite_run_args(args)):
            self.assertEqual((i,) + args, real_args)
            if i == 10:
                break

    def test_create_openstack_clients(self):
        #TODO(boris-42): Implement this method
        pass

    def test_manager_list_sizes(self):
        manager = fakes.FakeManager()

        def lst():
            return [1] * 10

        manager.list = lst
        manager_list_size = utils.manager_list_size([5])
        self.assertFalse(manager_list_size(manager))

        manager_list_size = utils.manager_list_size([10])
        self.assertTrue(manager_list_size(manager))

    def test_get_from_manager(self):
        get_from_manager = utils.get_from_manager()
        manager = fakes.FakeManager()
        resource = fakes.FakeResource(manager=manager)
        manager._cache(resource)
        self.assertEqual(get_from_manager(resource), resource)

    def test_get_from_manager_in_error_state(self):
        get_from_manager = utils.get_from_manager()
        manager = fakes.FakeManager()
        resource = fakes.FakeResource(manager=manager, status="ERROR")
        manager._cache(resource)
        self.assertRaises(exceptions.GetResourceFailure,
                          get_from_manager, resource)

    def test_get_from_manager_not_found(self):
        get_from_manager = utils.get_from_manager()
        manager = mock.MagicMock()
        resource = fakes.FakeResource(manager=manager, status="ERROR")

        class NotFoundException(Exception):
            http_status = 404

        manager.get = mock.MagicMock(side_effect=NotFoundException)
        self.assertRaises(exceptions.GetResourceFailure,
                          get_from_manager, resource)

    def test_get_from_manager_http_exception(self):
        get_from_manager = utils.get_from_manager()
        manager = mock.MagicMock()
        resource = fakes.FakeResource(manager=manager, status="ERROR")

        class HTTPException(Exception):
            pass

        manager.get = mock.MagicMock(side_effect=HTTPException)
        self.assertRaises(exceptions.GetResourceFailure,
                          get_from_manager, resource)

    @mock.patch('rally.benchmark.utils.create_openstack_clients')
    def test_prep_ssh_sec_group(self, mock_create_os_clients):
        fake_nova = fakes.FakeNovaClient()
        self.assertEqual(len(fake_nova.security_groups.list()), 1)
        mock_create_os_clients.return_value = {'nova': fake_nova}

        utils._prepare_for_instance_ssh('endpoint')

        self.assertEqual(len(fake_nova.security_groups.list()), 2)
        self.assertTrue(
            'rally_open' in
                [sg.name for sg in fake_nova.security_groups.list()]
        )

        # run prep again, check that another security group is not created
        utils._prepare_for_instance_ssh('endpoint')
        self.assertEqual(len(fake_nova.security_groups.list()), 2)

    @mock.patch('rally.benchmark.utils.create_openstack_clients')
    def test_prep_ssh_sec_group_rules(self, mock_create_os_clients):
        fake_nova = fakes.FakeNovaClient()

        #NOTE(hughsaunders) Default security group is precreated
        self.assertEqual(len(fake_nova.security_groups.list()), 1)
        mock_create_os_clients.return_value = {'nova': fake_nova}

        utils._prepare_for_instance_ssh('endpoint')

        self.assertEqual(len(fake_nova.security_groups.list()), 2)
        rally_open = fake_nova.security_groups.find('rally_open')
        self.assertEqual(len(rally_open.rules), 3)

        # run prep again, check that extra rules are not created
        utils._prepare_for_instance_ssh('endpoint')
        rally_open = fake_nova.security_groups.find('rally_open')
        self.assertEqual(len(rally_open.rules), 3)

    @mock.patch('rally.benchmark.utils.create_openstack_clients')
    def test_prep_ssh_keypairs(self, mock_create_os_clients):
        fake_nova = fakes.FakeNovaClient()
        self.assertEqual(len(fake_nova.keypairs.list()), 0)
        mock_create_os_clients.return_value = {'nova': fake_nova}

        utils._prepare_for_instance_ssh('endpoint')

        self.assertEqual(len(fake_nova.keypairs.list()), 1)
        self.assertTrue(
            'rally_ssh_key' in
                [sg.name for sg in fake_nova.keypairs.list()]
        )

        # run prep again, check that another keypair is not created
        utils._prepare_for_instance_ssh('endpoint')
        self.assertEqual(len(fake_nova.keypairs.list()), 1)