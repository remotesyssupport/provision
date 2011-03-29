import unittest

import libcloud

import provision.config as config
import provision.nodelib as nodelib

class TestDeploy(unittest.TestCase):
    def test_random_str(self):
        assert len(config.random_str()) == 6
    def test_flatten(self):
        assert [1,2,3,4] == nodelib.flatten([[1],[2,3],[4]])
    def test_unsplit_named_script_deployments(self):
        names = [s.name for s in
                 nodelib.named_script_deployments('foo.sh', 'l1\nl2\nl3\n')]
        assert ['foo.sh'] == names
    def test_split_named_script_deployments(self):
        names = [s.name for s in nodelib.named_script_deployments(
                'foo.sh', '# -*- split-lines: true; -*-\ns2\ns3')]
        assert ['foo_00.sh', 'foo_01.sh', 'foo_02.sh'] == names
    def test_node_deployment(self):
        nd = nodelib.Deployment(bundles=['mta'])
        assert nd.name.startswith(config.DEFAULT_NAME_PREFIX)
        assert libcloud.deployment.SSHKeyDeployment == type(nd.deployment.steps[0])

