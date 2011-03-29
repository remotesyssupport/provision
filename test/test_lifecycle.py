import unittest

import provision.config as config
import provision.nodelib as nodelib
import provision.meta as meta

class TestLifecycle(unittest.TestCase):

    """This test actually deploys and destroys a node, so it takes a long time to run"""

    def test_node_lifecycle(self):
        deployment = nodelib.Deployment()
        driver = nodelib.get_driver(config.DEFAULT_SECRET_KEY, config.DEFAULT_USERID,
                                    config.DEFAULT_PROVIDER)
        node = deployment.deploy(driver)
        import time; time.sleep(10)
        assert node.destroy()
        assert node.name not in [n.name for n in driver.list_nodes()]
        assert node.name not in meta.get_container((driver.key, driver.secret)).list_objects()
