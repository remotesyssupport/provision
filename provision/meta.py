from __future__ import absolute_import

import os
import cloudfiles

import provision.config as config
logger = config.logger

# cloudfiles values must have len(), so use strings rather than boolean
TRUE_VAL = 'True'
FALSE_VAL = 'False'

__doc__ = """Use cloudfiles to store node metadata

Specifically metadata about whether the node can be destroyed via the
provision library.

This module is non-portable to cloud providers other than rackspace.
However, the libcloud storage API, once implemented, should resolve
this issue.
"""

def get_container(creds, servicenet=False, name=config.NODE_METADATA_CONTAINER_NAME):
    logger.debug('connecting to %s' % creds[0])
    conn = cloudfiles.get_connection(*creds, servicenet=servicenet)
    logger.debug('connected to %s' % conn.connection_args[0])
    container = conn.create_container(name)
    logger.debug('using container %s' % container.name)
    return container

def set_destroyable(container, key, val=True):
    obj = container.get_object(key)
    obj.metadata['destroyable'] = TRUE_VAL if val else FALSE_VAL
    obj.sync_metadata()

def save_node_metadata(container, key, metadata, destroyable=False):
    obj = container.create_object(key)
    obj.metadata = metadata
    obj.metadata['destroyable'] = TRUE_VAL if destroyable else FALSE_VAL
    obj.load_from_filename(os.path.join(config.CODEPATH, 'empty')) # necessary, but can be 0 bytes
    logger.debug('metadata saved for node %s' % key)
    return obj

def delete_node_metadata(container, key):
    try:
        container.delete_object(key)
        logger.info('metadata deleted for node %s' % key)
    except:
        logger.exception('unable to delete metadata for node %s' % key)

def node_destroyable(container, key):
    try:
        obj = container.get_object(key)
        return obj.metadata.get('destroyable') == TRUE_VAL
    except:
        logger.debug('unable to get object metadata for key %s' % key)
        return False
