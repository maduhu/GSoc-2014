# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

#Test from the Marvin - Testing in Python wiki

#All tests inherit from cloudstackTestCase
from marvin.cloudstackTestCase import cloudstackTestCase

#Import Integration Libraries

from marvin.codes import FAILED
#base - contains all resources as entities and defines create, delete, list operations on them
from marvin.lib.base import Account, VirtualMachine, ServiceOffering, SimulatorMock

#utils - utility classes for common cleanup, external library wrappers etc
from marvin.lib.utils import cleanup_resources

#common - commonly used methods for all tests are listed here
from marvin.lib.common import get_zone, get_domain, get_template

from nose.plugins.attrib import attr

class TestDeployVM(cloudstackTestCase):
    """Test deploy a VM into a user account
    """

    def setUp(self):
        self.apiclient = self.testClient.getApiClient()

        self.testdata = self.testClient.getParsedTestDataConfig()
        
        # Get Zone, Domain and Default Built-in template
        self.domain = get_domain(self.apiclient)
        self.zone = get_zone(self.apiclient, self.testClient.getZoneForTests())
        self.testdata["mode"] = self.zone.networktype
        self.template = get_template(self.apiclient, self.zone.id, self.testdata["ostype"])

        if self.template == FAILED:
            self.fail("get_template() failed to return template with description %s" % self.testdata["ostype"])

        #create a user account
        self.account = Account.create(
            self.apiclient,
            self.testdata["account"],
            domainid=self.domain.id
        )
        #create a service offering
        self.service_offering = ServiceOffering.create(
            self.apiclient,
            self.testdata["service_offerings"]["small"]
        )
        #build cleanup list
        self.cleanup = [
            self.service_offering,
            self.account
        ]

    @attr(tags = ['advanced', 'simulator', 'basic', 'sg', 'selfservice'])
    def test_deploy_vm(self):
        """Test Deploy Virtual Machine

        # Validate the following:
        # 1. Virtual Machine is accessible via SSH
        # 2. listVirtualMachines returns accurate information
        """
        self.virtual_machine = VirtualMachine.create(
            self.apiclient,
            self.testdata["virtual_machine"],
            accountid=self.account.name,
            zoneid=self.zone.id,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            templateid=self.template.id
        )
        if not self.virtual_machine:
            self.fail("Deploying a Virtual Machine Failed")
        list_vms = VirtualMachine.list(self.apiclient, id=self.virtual_machine.id)
        self.debug(
            "Verify listVirtualMachines response for virtual machine: %s"\
            % self.virtual_machine.id
        )
        self.assertTrue(isinstance(list_vms, list) and len(list_vms) > 0, msg="List VM response empty")

        vm = list_vms[0]
        self.assertEqual(
            vm.id,
            self.virtual_machine.id,
            "Virtual Machine ids do not match"
        )
        self.assertEqual(
            vm.name,
            self.virtual_machine.name,
            "Virtual Machine names do not match"
        )
        self.assertEqual(
            vm.state,
            "Running",
            msg="VM is not in Running state"
        )

    @attr(tags = ['advanced', 'simulator', 'basic', 'sg', 'selfservice'])
    def test_deploy_vm_multiple(self):
        """Test Multiple Deploy Virtual Machine

        # Validate the following:
        # 1. deploy 2 virtual machines 
        # 2. listVirtualMachines using 'ids' parameter returns accurate information
        """
        self.virtual_machine = VirtualMachine.create(
            self.apiclient,
            self.testdata["virtual_machine"],
            accountid=self.account.name,
            zoneid=self.zone.id,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            templateid=self.template.id
        )

        self.virtual_machine2 = VirtualMachine.create(
            self.apiclient,
            self.testdata["virtual_machine2"],
            accountid=self.account.name,
            zoneid=self.zone.id,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            templateid=self.template.id
        )

        list_vms = VirtualMachine.list(self.apiclient, ids=[self.virtual_machine.id, self.virtual_machine2.id], listAll=True)
        self.debug(
            "Verify listVirtualMachines response for virtual machines: %s, %s" % (self.virtual_machine.id, self.virtual_machine2.id)
        )
        self.assertEqual(
            isinstance(list_vms, list),
            True,
            "List VM response was not a valid list"
        )
        self.assertEqual(
            len(list_vms),
            2,
            "List VM response was empty, expected 2 VMs"
        )

    def tearDown(self):
        try:
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            self.debug("Warning! Exception in tearDown: %s" % e)

class TestDeployVMVolumeCreationFailure(cloudstackTestCase):
    """Test VM deploy into user account with volume creation failure
    """

    def setUp(self):
        self.testdata =  self.testClient.getParsedTestDataConfig()
        self.apiclient = self.testClient.getApiClient()

        # Get Zone, Domain and Default Built-in template
        self.domain = get_domain(self.apiclient)
        self.zone = get_zone(self.apiclient, self.testClient.getZoneForTests())
        self.testdata["mode"] = self.zone.networktype
        self.template = get_template(self.apiclient, self.zone.id, self.testdata["ostype"])

        #create a user account
        self.account = Account.create(
            self.apiclient,
            self.testdata["account"],
            domainid=self.domain.id
        )
        #create a service offering
        self.service_offering = ServiceOffering.create(
            self.apiclient,
            self.testdata["service_offerings"]["small"]
        )
        #create first VM
        self.virtual_machine = VirtualMachine.create(
            self.apiclient,
            self.testdata["virtual_machine"],
            accountid=self.account.name,
            zoneid=self.zone.id,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            templateid=self.template.id)
        #mock to simulate volume creation failure
        self.mock_volume_failure = SimulatorMock.create(
            apiclient=self.apiclient,
            command="CopyCommand",
            count=6)
        #build cleanup list
        self.cleanup = [
            self.service_offering,
            self.account,
            self.mock_volume_failure
        ]

    @attr(tags = ['selfservice'])
    def test_deploy_vm_volume_creation_failure(self):
        """Test Deploy Virtual Machine - volume creation failure and retry

        # Validate the following:
        # 1. 1st VM creation failed
        # 2. Check there were 4 failed volume creation retries (mock count = (6-4) = 2)
        # 3. 2nd VM creation succeeded
        # 4. Check there were 2 failed volume creation retries (mock count = (2-2) = 0)
        # 5. ListVM returns accurate information
        """
        self.virtual_machine = None
        with self.assertRaises(Exception):
            self.virtual_machine = VirtualMachine.create(
                self.apiclient,
                self.testdata["virtual_machine2"],
                accountid=self.account.name,
                zoneid=self.zone.id,
                domainid=self.account.domainid,
                serviceofferingid=self.service_offering.id,
                templateid=self.template.id)

        self.mock_volume_failure = self.mock_volume_failure.query(self.apiclient)
        self.assertEqual(
            self.mock_volume_failure.count,
            2,
            msg="Volume failure mock not executed")

        self.virtual_machine = VirtualMachine.create(
            self.apiclient,
            self.testdata["virtual_machine3"],
            accountid=self.account.name,
            zoneid=self.zone.id,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            templateid=self.template.id)
        list_vms = VirtualMachine.list(self.apiclient, id=self.virtual_machine.id)
        self.assertTrue(isinstance(list_vms, list) and len(list_vms) > 0, msg="List VM response empty")
        vm = list_vms[0]
        self.assertEqual(
            vm.id,
            self.virtual_machine.id,
            "VM ids do not match")
        self.assertEqual(
            vm.name,
            self.virtual_machine.name,
            "VM names do not match")
        self.assertEqual(
            vm.state,
            "Running",
            msg="VM is not in Running state")

        self.mock_volume_failure = self.mock_volume_failure.query(self.apiclient)
        self.assertEqual(
            self.mock_volume_failure.count,
            0,
            msg="Volume failure mock not executed")

    def tearDown(self):
        try:
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            self.debug("Warning! Exception in tearDown: %s" % e)


class TestDeployVMStartFailure(cloudstackTestCase):
    """Test VM deploy into user account with start operation failure
    """

    def setUp(self):
        self.testdata = self.testClient.getParsedTestDataConfig()
        self.apiclient = self.testClient.getApiClient()

        # Get Zone, Domain and Default Built-in template
        self.domain = get_domain(self.apiclient)
        self.zone = get_zone(self.apiclient, self.testClient.getZoneForTests())
        self.testdata["mode"] = self.zone.networktype
        self.template = get_template(self.apiclient, self.zone.id, self.testdata["ostype"])

        #create a user account
        self.account = Account.create(
            self.apiclient,
            self.testdata["account"],
            domainid=self.domain.id
        )
        #create a service offering
        self.service_offering = ServiceOffering.create(
            self.apiclient,
            self.testdata["service_offerings"]["small"]
        )
        #create first VM
        self.virtual_machine = VirtualMachine.create(
            self.apiclient,
            self.testdata["virtual_machine"],
            accountid=self.account.name,
            zoneid=self.zone.id,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            templateid=self.template.id)
        #mock to simulate vm start failure
        self.mock_start_failure = SimulatorMock.create(
            apiclient=self.apiclient,
            command="StartCommand",
            count=6)
        #build cleanup list
        self.cleanup = [
            self.service_offering,
            self.account,
            self.mock_start_failure
        ]

    @attr(tags = ['selfservice'])
    def test_deploy_vm_start_failure(self):
        """Test Deploy Virtual Machine - start operation failure and retry

        # Validate the following:
        # 1. 1st VM creation failed
        # 2. Check there were 4 failed start operation retries (mock count = (6-4) = 2)
        # 3. 2nd VM creation succeeded
        # 4. Check there were 2 failed start operation retries (mock count = (2-2) = 0)
        # 5. ListVM returns accurate information
        """
        self.virtual_machine = None
        with self.assertRaises(Exception):
            self.virtual_machine = VirtualMachine.create(
                self.apiclient,
                self.testdata["virtual_machine2"],
                accountid=self.account.name,
                zoneid=self.zone.id,
                domainid=self.account.domainid,
                serviceofferingid=self.service_offering.id,
                templateid=self.template.id)

        self.mock_start_failure = self.mock_start_failure.query(self.apiclient)
        self.assertEqual(
            self.mock_start_failure.count,
            2,
            msg="Start failure mock not executed")

        self.virtual_machine = VirtualMachine.create(
            self.apiclient,
            self.testdata["virtual_machine3"],
            accountid=self.account.name,
            zoneid=self.zone.id,
            domainid=self.account.domainid,
            serviceofferingid=self.service_offering.id,
            templateid=self.template.id)
        list_vms = VirtualMachine.list(self.apiclient, id=self.virtual_machine.id)
        self.assertTrue(isinstance(list_vms, list) and len(list_vms) > 0, msg="List VM response empty")
        vm = list_vms[0]
        self.assertEqual(
            vm.id,
            self.virtual_machine.id,
            "VM ids do not match")
        self.assertEqual(
            vm.name,
            self.virtual_machine.name,
            "VM names do not match")
        self.assertEqual(
            vm.state,
            "Running",
            msg="VM is not in Running state")

        self.mock_start_failure = self.mock_start_failure.query(self.apiclient)
        self.assertEqual(
            self.mock_start_failure.count,
            0,
            msg="Start failure mock not executed")

    def tearDown(self):
        try:
            cleanup_resources(self.apiclient, self.cleanup)
        except Exception as e:
            self.debug("Warning! Exception in tearDown: %s" % e)


