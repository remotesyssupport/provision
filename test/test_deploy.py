import unittest

import libcloud

import provision.config as config
import provision.nodelib as nodelib

class TestDeploy(unittest.TestCase):

    def test_random_str(self):
        assert len(config.random_str()) == 6

    def test_unsplit_named_script_deployments(self):
        assert 'foo.sh' == \
            nodelib.script_deployment('foo.sh', 'l1\nl2\nl3\n').name

    def test_node_deployment(self):
        nd = nodelib.Deployment(bundles=['mta'])
        assert nd.name.startswith(config.DEFAULT_NAME_PREFIX)
        assert libcloud.deployment.SSHKeyDeployment == type(nd.deployment.steps[0])
