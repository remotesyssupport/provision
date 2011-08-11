"""Implementation of node listing, deployment and destruction"""

from __future__ import absolute_import

import datetime
import itertools
import json
import os
import re
import string

import libcloud.providers
import libcloud.deployment

import provision.config as config
import provision.collections
logger = config.logger


def get_driver(secret_key=config.DEFAULT_SECRET_KEY, userid=config.DEFAULT_USERID,
               provider=config.DEFAULT_PROVIDER):

    """A driver represents successful authentication.  They become
    stale, so obtain them as late as possible, and don't cache them."""

    logger.debug('get_driver {0}@{1}'.format(userid, provider))
    return libcloud.providers.get_driver(config.PROVIDERS[provider])(userid, secret_key)


def list_nodes(driver):
    logger.debug('list_nodes')
    return driver.list_nodes()


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

        """Insure only destroyable nodes are destroyed"""

        node = self.node
        if not config.is_node_destroyable(node.name):
            logger.error('node %s has non-destroyable prefix' % node.name)
            return False
        logger.info('destroying node %s' % node)
        return node.destroy()

    def sum_exit_status(self):
        """Return the sum of all deployed scripts' exit_status"""
        return sum([sd.exit_status for sd in self.node.script_deployments])


def substitute(script, submap):

    """Check for presence of template indicator and if found, perform
    variable substition on script based on template type, returning
    script."""

    match = config.TEMPLATE_RE.search(script)
    if match:
        template_type = match.groupdict()['type']
        try:
            return config.TEMPLATE_TYPEMAP[template_type](script, submap)
        except KeyError:
            logger.error('Unsupported template type: %s' % template_type)
            raise
    return script


def script_deployment(path, script, submap=None):

    """Return a ScriptDeployment from script with possible template
    substitutions."""

    if submap is None:
        submap = {}
    script = substitute(script, submap)
    return libcloud.deployment.ScriptDeployment(script, path)


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
                 prefix=config.DEFAULT_NAME_PREFIX, image_name=config.DEFAULT_IMAGE_NAME,
                 subvars=[]):

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
        to be run.

        The image_name is used to determine which set of default
        bundles to install, as well as to actually get the image id in
        deploy()."""

        self.name = name or prefix + config.random_str()
        config.SUBMAP['node_name'] = self.name
        merge_keyvals_into_map(subvars, config.SUBMAP)
        logger.debug('substitution map {0}'.format(config.SUBMAP))

        self.pubkeys = [pubkey]
        self.pubkeys.extend(config.PUBKEYS)

        self.image_name = image_name

        self.filemap = {}
        scriptmap = provision.collections.OrderedDict() # preserve script run order

        if image_name in config.BOOTSTRAPPED_IMAGE_NAMES:
            install_bundles = config.DEFAULT_BUNDLES[:]
        else:
            install_bundles = config.DEFAULT_BOOTSTRAP_BUNDLES[:]
        install_bundles.extend(bundles)

        for bundle in install_bundles:
            logger.debug('loading bundle {0}'.format(bundle))
            merge_load(config.BUNDLEMAP[bundle].filemap.items(), self.filemap)
            merge_load(config.BUNDLEMAP[bundle].scriptmap.items(), scriptmap)
        logger.debug('files {0}'.format(self.filemap.keys()))
        logger.debug('scripts {0}'.format(scriptmap.keys()))

        self.script_deployments = [script_deployment(path, script, config.SUBMAP)
                                   for path, script in scriptmap.items()]
        logger.debug('len(script_deployments) = {0}'.format(len(self.script_deployments)))

        steps = [libcloud.deployment.SSHKeyDeployment(''.join(self.pubkeys))]
        steps.extend(self.script_deployments)
        self.deployment = libcloud.deployment.MultiStepDeployment(steps)

    def deploy(self, driver, location_id=config.DEFAULT_LOCATION_ID,
               size_id=config.DEFAULT_SIZE_ID):

        """Use driver to deploy node, with optional ability to specify
        location id and size id.

        First, obtain location object from driver.  Next, get the
        size.  Then, get the image. Finally, deploy node, and return
        NodeProxy. """

        logger.debug('deploying node %s using driver %s' % (self.name, driver))
        location = driver.list_locations()[location_id]
        logger.debug('location %s' % location)
        size = driver.list_sizes()[size_id]
        logger.debug('size %s' % size)
        image = image_from_name(config.IMAGE_NAMES[self.image_name], driver.list_images())
        logger.debug('image %s' % image)

        logger.debug('starting node deployment with %s steps' % len(self.deployment.steps))
        node = driver.deploy_node(name=self.name, ex_files=self.filemap, deploy=self.deployment,
                                  location=location, image=image, size=size)
        node.script_deployments = self.script_deployments # retain exit_status, stdout, stderr
        return NodeProxy(node)


def image_from_name(name, images):

    """Return an image from a list of images.  If the name is an exact
    match, return the last exactly matching image.  Otherwise, sort
    images by 'natural' order, using decorate-sort-undecorate, and
    return the largest.

    see:
    http://code.activestate.com/recipes/285264-natural-string-sorting/
    """

    prefixed_images = [i for i in images if i.name.startswith(name)]

    if name in [i.name for i in prefixed_images]:
        return [i for i in prefixed_images if i.name == name][-1]

    decorated = sorted(
        [(int(re.search('\d+', i.name).group(0)), i) for i in prefixed_images])
    return [i[1] for i in decorated][-1]


def destroy_by_name(name, driver):

    """Destroy all nodes matching specified name"""

    matches = [node for node in list_nodes(driver) if node.name == name]
    if len(matches) == 0:
        logger.warn('no node named %s' % name)
        return False
    else:
        return all([node.destroy() for node in matches])
