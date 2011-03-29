import unittest

import provision.config as config
import provision.meta as meta

class TestMeta(unittest.TestCase):

    """This test makes several network API calls, so it takes a few seconds to run"""

    def test_meta_destroyable(self):
        creds = (config.DEFAULT_USERID, config.DEFAULT_SECRET_KEY)
        container = meta.get_container(creds)
        key = 'key_' + config.random_str()
        assert not meta.node_destroyable(container, key)
        meta.save_node_metadata(container, key, {}, destroyable=True)
        assert meta.node_destroyable(container, key)
        meta.delete_node_metadata(container, key)
        assert not meta.node_destroyable(container, key)
        meta.save_node_metadata(container, key, {}, destroyable=False)
        assert not meta.node_destroyable(container, key)
        meta.delete_node_metadata(container, key)

