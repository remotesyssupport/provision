import unittest

import provision.config as config

class Test(unittest.TestCase):

    def setUp(self):
        self.destroyable_prefixes = ['deploy-test-', 'demo-']

    def test_destroyable(self):
        assert config.is_node_destroyable('deploy-test-123', self.destroyable_prefixes)
        assert config.is_node_destroyable('demo-123', self.destroyable_prefixes)

    def test_not_destroyable(self):
        assert not config.is_node_destroyable('trac-server', self.destroyable_prefixes)
        assert not config.is_node_destroyable('demo', self.destroyable_prefixes)

