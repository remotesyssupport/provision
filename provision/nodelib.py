from __future__ import absolute_import

import datetime
import itertools
import json
import os

import libcloud.providers
import libcloud.deployment

import provision.meta as meta
import provision.config as config
logger = config.logger


__doc__ = """Implementation of node listing, deployment and destruction"""

def get_driver(secret_key=config.DEFAULT_SECRET_KEY, userid=config.DEFAULT_USERID,
               provider=config.DEFAULT_PROVIDER):

    """A driver represents successful authentication.  They become
    stale, so obtain them as late as possible, and don't cache them."""

    logger.debug('get_driver {0}@{1}'.format(userid, provider))
    return libcloud.providers.get_driver(config.PROVIDERS[provider])(userid, secret_key)


def list_nodes(driver):
    logger.debug('list_nodes')
    return driver.list_nodes()


def flatten(lst):
    return list(itertools.chain(*lst))


class NodeProxy(object):

    """Wrap a libcloud.base.Node object and adds some functionality"""

    def __init__(self, node):
        self.node = node

    def __getattr__(self, name):
        return getattr(self.node, name)

    def write_json(self, path):
        info = {
            'id': self.node.id,
            'name': self.node.name,
            'state': self.node.state,
            'public_ip': self.node.public_ip,
            'private_ip': self.node.private_ip}
        with open(path, 'wb') as df:
            json.dump(info, df)
            df.close()

    def __repr__(self):
        s = self.node.__repr__()
        if self.node.script_deployments:
            s += '\n'.join(
                ['*{0.name}: {0.exit_status}\n{0.script}\n{0.stdout}\n{0.stderr}'.format(sd)
                 for sd in self.node.script_deployments])
        return s

    def destroy(self):

        """Perform failsafe checks to insure only expendable nodes are destroyed"""

        node = self.node
        if config.NODE_METADATA_CONTAINER_NAME:
            container = meta.get_container(creds=(node.driver.key, node.driver.secret))
            if not meta.node_destroyable(container, node.name):
                logger.error('metadata does not indicate node %s is destroyable' % node.name)
                return False
            meta.delete_node_metadata(container, node.name)
        else:
            if all([not node.name.startswith(pre) for pre in config.DESTROYABLE_PREFIXES]):
                logger.error('node %s has non-destroyable prefix' % node.name)
                return False
        logger.info('destroying node %s' % node)
        return node.destroy()


def named_script_deployments(path, script, submap=None):

    """Perform variable substition on script, possibly breaking into
    separate scripts per line, and return a list of ScriptDeployments."""

    if submap is None:
        submap = {}

    if config.SPLIT_RE.search(script):
        lines = script.split('\n')
        deployments = []
        base, ext = os.path.splitext(path)
        for number, line in enumerate(lines):
            linepath = '%s_%02d%s' % (base, number, ext) #TODO: smarter or configurable
            deployments.append(
                libcloud.deployment.ScriptDeployment(line.format(**submap), linepath))
        return deployments
    else:
        return [libcloud.deployment.ScriptDeployment(script.format(**submap), path)]


def merge_load(items, amap):

    """Merge list of tuples into dict amap and load source as value"""

    for target, source in items:
        if amap.get(target):
            logger.warn('overwriting {0}'.format(target))
        amap[target] = open(source).read()


def merge_keyvals_into_map(keyvals, amap):

    """Merge list of 'key=val' strings into dict amap, warning of duplicate keys"""

    for kv in keyvals:
        k,v = kv.split('=')
        if k in amap:
            logger.warn('overwriting {0} with {1}'.format(k, v))
        amap[k] = v


class Deployment(object):

    """Split the deployment process into two steps"""

    def __init__(self, name=None, bundles=[], pubkey=config.DEFAULT_PUBKEY,
                 prefix=config.DEFAULT_NAME_PREFIX, subvars=[]):

        """Initialize a node deployment.

        If name is not given, it will generate a random name using
        prefix.  The node name is added to the global substitution
        map, which is used to parameterize templates in scripts
        containing the form {variable_name}.

        The list of bundle names is concatenated with any globally
        common bundle names from which result the set of files to be
        installed, and scripts to be run on the new node.

        The pubkey is concatented with any other public keys loaded
        during configuration and used as the first step in the
        multi-step deployment.  Additional steps represent the scripts
        to be run."""

        #logger.debug('Deployment.__init__()')
        self.name = name or prefix + config.random_str()
        config.SUBMAP['node_name'] = self.name
        merge_keyvals_into_map(subvars, config.SUBMAP)
        logger.debug('substitution map {0}'.format(config.SUBMAP))

        self.pubkeys = [pubkey]
        self.pubkeys.extend(config.PUBKEYS)

        self.filemap = {}
        scriptmap = {}
        for bundle in config.COMMON_BUNDLES + bundles:
            logger.debug('loading bundle {0}'.format(bundle))
            merge_load(config.BUNDLEMAP[bundle].filemap.items(), self.filemap)
            merge_load(config.BUNDLEMAP[bundle].scriptmap.items(), scriptmap)
        logger.debug('files {0}'.format(self.filemap.keys()))
        logger.debug('scripts {0}'.format(scriptmap.keys()))

        self.script_deployments = flatten(
            [named_script_deployments(path, script, config.SUBMAP)
             for path, script in scriptmap.items()])
        logger.debug('len(script_deployments) = {0}'.format(len(self.script_deployments)))

        steps = [libcloud.deployment.SSHKeyDeployment(''.join(self.pubkeys))]
        steps.extend(self.script_deployments)
        self.deployment = libcloud.deployment.MultiStepDeployment(steps)

    def deploy(self, driver, location_id=config.DEFAULT_LOCATION_ID,
               size_id=config.DEFAULT_SIZE_ID, image_name=config.DEFAULT_IMAGE_NAME):

        """Use driver to deploy node, with optional ability to specify
        location id, size id and image name.

        First, obtain location object from driver.  Next, get the
        size.  Then, get the image.

        If using cloudfiles and have specified metadata container
        name, save relevant information to cloudfiles.

        Finally, deploy node, and return NodeProxy. """

        logger.debug('deploying node %s using driver %s' % (self.name, driver))
        location = driver.list_locations()[location_id]
        logger.debug('location %s' % location)
        size = driver.list_sizes()[size_id]
        logger.debug('size %s' % size)
        image = [i for i in driver.list_images()
                 if i.name == config.IMAGE_NAMES[image_name]][0]
        logger.debug('image %s' % image)

        self.metadata = {'created': str(datetime.datetime.now())}
        if config.NODE_METADATA_CONTAINER_NAME:
            meta.save_node_metadata(meta.get_container(creds=(driver.key, driver.secret)),
                                    self.name, self.metadata,
                                    destroyable=any([self.name.startswith(p)
                                                     for p in config.DESTROYABLE_PREFIXES]))
        logger.debug('starting node deployment with %s steps' % len(self.deployment.steps))
        node = driver.deploy_node(name=self.name, ex_files=self.filemap, deploy=self.deployment,
                                  location=location, image=image, size=size)
        node.script_deployments = self.script_deployments # retain exit_status, stdout, stderr
        return NodeProxy(node)

def destroy_by_name(name, driver):

    """Destroy all nodes matching specified name"""

    matches = [node for node in list_nodes(driver) if node.name == name]
    if len(matches) == 0:
        logger.warn('no node named %s' % name)
        return False
    else:
        return all([node.destroy() for node in matches])
