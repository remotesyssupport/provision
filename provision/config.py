from __future__ import print_function

"""Configuration of provision apps is a two step process.

The first step specifies which directories to use for configuring
defaults, defining resource bundles, setting API keys and which public
keys to trust. This allows users to use site-specific configuration
directories outside the source tree.

The second step specifies which bundles to install on the new node,
and any other details specific to the deployment.

Each bundle represents a set of files to be copied and scripts to be
run during node deployment."""

import argparse
import os.path
import random
import re
import string
import sys
import traceback

import socket; socket.setdefaulttimeout(600.0) # give APIs 10 minutes

import libcloud.types

import provision.collections

join = os.path.join

PROVIDERS = {
    'rackspace': libcloud.types.Provider.RACKSPACE}

IMAGE_NAMES = {
    'karmic': 'Ubuntu 9.10 (karmic)',
    'lucid': 'Ubuntu 10.04 LTS (lucid)',
    'maverick': 'Ubuntu 10.10 (maverick)',
    'natty': 'Ubuntu 11.04 (Natty)'}

DEFAULT_IMAGE_NAME = 'lucid'
DEFAULT_LOCATION_ID = 0
DEFAULT_SIZE_ID = 0

DEFAULT_PUBKEY = open(os.path.expanduser('~/.ssh/id_rsa.pub')).read()

# Note that the last directory in the path cannot start with a '.'
# due to module naming restrictions
LOCAL_DEFAULTS = os.path.expanduser('~/.provision/secrets')

VIRTUAL_ENV = os.getenv('VIRTUAL_ENV')
VIRTUAL_DEFAULTS = join(VIRTUAL_ENV, 'provision_secrets') if VIRTUAL_ENV else ''

DEFAULT_TARGETDIR = '/root/deploy'

DEFAULT_NAME_PREFIX = 'deploy-test-'

DESTROYABLE_PREFIXES = [DEFAULT_NAME_PREFIX]

# Set to None or '' to ignore metadata
NODE_METADATA_CONTAINER_NAME = 'node_meta'

#SPLIT_RE = re.compile('split-lines:\W*true', re.IGNORECASE)
TEMPLATE_RE = re.compile('#.+provision-template-type:\W*(?P<type>[\w-]+)')

TEMPLATE_TYPEMAP = {
    # http://docs.python.org/library/string.html#format-string-syntax
    'format-string': lambda text, submap: text.format(**submap),
    # http://docs.python.org/library/string.html#template-strings
    'template-string': lambda text, submap: string.Template(text).safe_substitute(submap),
    }

CODEPATH = os.path.dirname(__file__)

SCRIPTSDIR = 'scripts'
FILESDIR = 'files'
PUBKEYSDIR = 'pubkeys'

PUBKEYS = []
SUBMAP = {}
BUNDLEMAP = {}

BOOTSTRAPPED_IMAGE_NAMES = []
DEFAULT_BUNDLES = [] # these get installed if image name in BOOTSTRAPPED_IMAGE_NAMES
DEFAULT_BOOTSTRAP_BUNDLES = [] # otherwise these get installed

PATH = None

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger('provision')


# error codes for corresponding exceptions
EXCEPTION = 11
MALFORMED_RESPONSE = 12
SERVICE_UNAVAILABLE = 13
DEPLOYMENT_ERROR = 14
TIMEOUT = 15

def handle_errors(callback, parsed=None, out=sys.stderr):

    """Execute the callback, optionally passing it parsed, and return
    its return value.  If an exception occurs, determine which kind it
    is, output an appropriate message, and return the corresponding
    error code."""

    try:
        if parsed:
            return callback(parsed)
        else:
            return callback()
    except libcloud.types.DeploymentError as e:
        traceback.print_exc(file=out)
        print(e, file=out)
        if hasattr(e, 'value') and hasattr(e.value, 'args') and len(e.value.args) > 0 and \
                'open_sftp_client' in e.value.args[0]:
            print('Timeout', file=out)
            return TIMEOUT
        return DEPLOYMENT_ERROR
    except libcloud.types.MalformedResponseError as e:
        traceback.print_exc(file=out)
        print(e, file=out)
        if 'Service Unavailable' in e.body:
            return SERVICE_UNAVAILABLE
        return MALFORMED_RESPONSE
    except SystemExit:
        pass
    except:
        traceback.print_exc(file=out)
        return EXCEPTION


class Bundle(object):

    """Encapsulates mappings from file and script paths on the target
    node to their local, source paths"""

    def __init__(self, scriptmap=None, filemap=None):
        """
        @type scriptmap: C{dict}
        @keyword scriptmap: Maps target path to source path for scripts

        @type filemap: C{dict}
        @keyword filemap: Maps target path to source path for files
        """
        self.scriptmap = scriptmap or provision.collections.OrderedDict()
        self.filemap = filemap or {}

def makemap(filenames, sourcedir, targetdir=None):

    """Return an OrderedDict (to preserve script run order) which maps
    filenames coming from a single local source directory to a single
    target directory.  Most useful for scripts, whose location when
    run is often unimportant, and so can all be placed in common
    directory."""

    if targetdir is None: targetdir = DEFAULT_TARGETDIR
    return provision.collections.OrderedDict(
        (join(targetdir, f),  join(sourcedir, f)) for f in filenames)

def add_bundle(name, scripts=[], files=[], scriptsdir=SCRIPTSDIR, filesdir=FILESDIR):

    """High level, simplified interface for creating a bundle which
    takes the bundle name, a list of script file names in a common
    scripts directory, and a list of absolute target file paths, of
    which the basename is also located in a common files directory.
    It converts those lists into maps and then calls new_bundle() to
    actually create the Bundle and add it to BUNDLEMAP"""

    scriptmap = makemap(scripts, join(PATH, scriptsdir))
    filemap = dict(zip(files, [join(PATH, filesdir, os.path.basename(f)) for f in files]))
    new_bundle(name, scriptmap, filemap)

def new_bundle(name, scriptmap, filemap=None):

    """Create a bundle and add to available bundles"""

    #logger.debug('new bundle %s' % name)
    if name in BUNDLEMAP:
        logger.warn('overwriting bundle %s' % name)
    BUNDLEMAP[name] = Bundle(scriptmap, filemap)

def random_str(length=6, charspace=string.ascii_lowercase+string.digits):
    return ''.join(random.sample(charspace, length))

class DictObj(object):

    """Wraps a dict so its keys are accessed like properties, using dot notation"""

    def __init__(self, d):
        self.__dict__['d'] = d

    def __setattr__(self, key, value):
        if self.__dict__['d'].get(key):
            logger.warn('overwriting config.{0}'.format(key))
        self.__dict__['d'][key] = value

    def __getattr__(self, key):
        return self.__dict__['d'][key]


def import_by_path(path):

    """Append the path to sys.path, then attempt to import module with
    path's basename, finally making certain to remove appended path.

    http://stackoverflow.com/questions/1096216/override-namespace-in-python"""

    sys.path.append(os.path.dirname(path))
    try:
        return __import__(os.path.basename(path))
    except ImportError:
        logger.warn('unable to import {0}'.format(path))
    finally:
        del sys.path[-1]

def init_module(path):

    """Attempt to import a Python module located at path.  If
    successful, and if the newly imported module has an init()
    function, then set the global PATH in order to simplify the
    add_bundle() interface and call init() on the module, passing the
    current global namespace, conveniently converted into a DictObj so
    that it can be accessed with normal module style dot notation
    instead of as a dict.

    http://stackoverflow.com/questions/990422/how-to-get-a-reference-to-current-modules-attributes-in-python"""

    mod = import_by_path(path)
    if mod is not None and hasattr(mod, 'init'):
        logger.debug('calling init on {0}'.format(mod))
        global PATH
        PATH = path
        mod.init(DictObj(globals()))

def load_pubkeys(loadpath, pubkeys):

    """Append the file contents in loadpath directory onto pubkeys list"""

    filenames = os.listdir(loadpath)
    logger.debug('loading authorized pubkeys {0}'.format(filenames))
    for filename in filenames:
        pubkeys.append(open(join(loadpath, filename)).read())

def normalize_path(path, relative_to=os.getcwd()):

    """Return normalized path.  If path is not user-expandable or
    absolute, treat it relative to relative_to"""

    path = os.path.expanduser(os.path.normpath(path))

    if os.path.isabs(path):
        return path
    else:
        return join(relative_to, path)

def configure(paths, relative_to):

    """Iterate on each configuration path, collecting all public keys
    destined for the new node's root account's authorized keys.
    Additionally attempt to import path as python module."""

    if not paths:
        return
    for path in [normalize_path(p, relative_to) for p in paths]:
        logger.debug('configuration path {0}'.format(path))
        pubkeys_path = join(path, PUBKEYSDIR)
        if os.path.exists(pubkeys_path):
            load_pubkeys(pubkeys_path, PUBKEYS)
        init_module(path)

def parser():

    """Return a parser for setting one or more configuration paths"""

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config_paths', default=[], action='append',
                        help='path to a configuration directory')
    return parser

def add_auth_args(parser, config):

    """Return a parser for configuring authentication parameters"""

    parser.add_argument('-p', '--provider', default=config.DEFAULT_PROVIDER)
    parser.add_argument('-u', '--userid', default=config.DEFAULT_USERID)
    parser.add_argument('-k', '--secret_key', default=config.DEFAULT_SECRET_KEY)
    return parser

def reconfig(main_parser, args=sys.argv[1:]):

    """Parse any config paths and reconfigure defaults with them
    http://docs.python.org/library/argparse.html#partial-parsing
    Return parsed remaining arguments"""

    parsed, remaining_args = parser().parse_known_args(args)
    configure(parsed.config_paths, os.getcwd())
    return main_parser().parse_args(remaining_args)

defaults = ['defaults']
if os.path.exists(LOCAL_DEFAULTS):
    defaults.append(LOCAL_DEFAULTS)
if os.path.exists(VIRTUAL_DEFAULTS):
    defaults.append(VIRTUAL_DEFAULTS)
configure(defaults, CODEPATH)

