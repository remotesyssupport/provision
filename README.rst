=========
Provision
=========

Philosophy
==========

Provision makes it easy to create cloud servers with complicated
configurations from the command line.

Introduction
============

Provision enables users to deploy customized nodes, either via shell
commands, or as a Python library.  Building on Apache Libcloud, which
provides a common API for various providers, Provision allows users to
specify, for a new node, which files get installed, which scripts get
run, and which public keys have access, in a flexible yet repeatable
way.  Provision has been tested using Rackspace and Amazon AWS.

In addition to basic configuration decisions (such as provider, disk
image, size, location, and name), Provision supports four conceptually
distinct components that determine how a node gets deployed.

#. Public keys that grant their respective private keys root access on
   the deployed node.

#. Files that get copied into their specified location on the node.

#. Script templates supporting run time variable substitution that get
   run on the node.

#. Minimal Python configuration code for setting secret keys, creating
   named bundles of scripts and files for specific functionality, etc.

Provision applications are themselves automatically configured from
the provision/defaults directory and optional, additional
configuration directories which themselves contain an __init__.py
file, and possible subdirectories of files, scripts and public keys.

These additional configuration directories can be used to change the
default configuration parameters in any way, and are typically used to
set secret API keys, access keys, and define provider-specific
functionality bundles.

A Bundle is a named collection of files and scripts that will get
installed and run on the deployed node.  You can specify a default set
of Bundle names that will get installed for every new node, as well as
specifying which additional bundles to install via command line or
library interface.


Dependencies
============

See setup.py for details on version requirements.  The following
modules will be automatically installed if not present.

* apache-libcloud
* paramiko
* pycrypto
* argparse
* cloudfiles (optional)


Installation
============

Provision uses distribute.setuptools for installation and test running.

To install, cd to top level directory and run::

   $ python setup.py install

To run tests, cd to top level directory and run::

   $ python setup.py test


Usage
=====

Shell Commands
--------------

The following shell commands are available after installation:

* deploy-node
    Typical usage: $ deploy-node -c ~/secrets_dir -b dev
  
* list-nodes
    Typical usage: $ list-nodes -c ~/secrets_dir
  
* destroy-node
    Typical usage: $ destroy-node -c ~/secrets_dir nodename

Several command line arguments are common to all three commands:

* -c --config-paths
    Specify path to a configuration directory. Can be used multiple times.

* -p --provider
    Specify provider (defaults to config.DEFAULT_PROVIDER)

* -u --userid
    Specify user id (defaults to config.DEFAULT_USERID)

* -k --secret_key
    Specify secret key (defaults to config.DEFAULT_SECRET_KEY)

Other command line arguments are specific to individual commands

deploy-node
^^^^^^^^^^^

* -b --bundles
    Specify names of bundles to install.  Can be used multiple times.

* -d --description-file
    If specified, output node description in json format to file.

* -i --image
    Specify image name (defaults to config.DEFAULT_IMAGE_NAME)

* -l --location
    Specify location id (defaults to config.DEFAULT_LOCATION_ID)

* -n --name
     Generate randomized name based on prefix if name not specified.

* -s --size
    Specify node size (defaults to config.DEFAULT_SIZE_ID)

* -t --subvars
     Key=value pairs of template substitution variables. Can be used multiple times.

* -x --prefix
    Use prefix to generate randomized name (defaults to config.DEFAULT_NAME_PREFIX)

destroy-node
^^^^^^^^^^^^

* name
    The name of the node to destroy

* -t --testresults
    Only destroy node if all tests passed in specified junit-style XML formatted file

Configuration Directory Structure
---------------------------------

Provision is not particulary useful out of the box.  At the minimum,
you will need to specify which provider, user id, and secret key to
use to access your account.  This can all be done on the command line,
but it's can be simpler to create a local configuration directory and
either specify its location on the command line, or put it in a
default location that provision will try to load on startup.

Aside from authentication, a configuration directory can be use to
define bundles of associated files and scripts that will get run when
a node is deployed.  It can also read and write any variable defined
in the provision.config module, which gives great flexibility in
determining how the program will act by default.

Provision configuration directories all share the same structure.  At
the top level is a __init__.py file, which gets imported and its
init() function executed during configuration time.

Also at the top level are three directories called "pubkeys",
"scripts", and "files".  Provision uses libcloud, which uses public
key cryptography by default to communicate with the new node.  During
a deploy, it will by default look for the file ~/.ssh/id_rsa.pub and
insert it into the node's /root/.ssh/authorized_keys file.  If it
exists and contains files, provision will also include those public
keys in the new node's authorized_keys.

From the other two directories, files and scripts get loaded into
memory, and are mapped into bundles in __init__.py, which can then be
specified in the command line using -b bundle-name, or added to
DEFAULT_BUNDLES, to get installed for every deploy.

It is sometimes useful to be able to substitute variables into scripts
at runtime.  This can be done by using the --subvars command line
option with script templating.

Embed one of the following lines in a script to activate variable
substitution::

    # provision-template-type: format-string
    or
    # provision-template-type: template-string

See `format string documentation
<http://docs.python.org/library/string.html#format-string-syntax>`_
and `template strings documentation
<http://docs.python.org/library/string.html#template-strings>`_ for
the respective syntaxes.  Also see test cases in
test_script_templates.py.

The __init__.py file can also be used to override default settings in
the provision.config module, which gets passed into init() as a
parameter.

This is an example of an __init__.py file::

    def init(config):
        config.DEFAULT_PROVIDER = 'rackspace'
        config.DEFAULT_USERID = 'user1'
        config.DEFAULT_SECRET_KEY = 'somehardtoguesssecret'

        config.DEFAULT_BOOTSTRAP_BUNDLES.extend(['tz', 'snmpd']
        config.DEFAULT_BUNDLES.extend(['security'])

        config.add_bundle('dev', ['emacs.sh', 'screen.sh'],
                          ['/root/.emacs.d/init.el', '/root/.screenrc'])


For this example, the files directory contains init.el, which will get
installed at /root/emacs.d/init.el in the deployed node, and .screenrc
which gets installed and /root/.screenrc.

Similarly, the scripts directory contains emacs.sh and screen.sh,
which get executed on the deployed node after it boots for the first
time.


Default Configuration Directory Locations
-----------------------------------------

When provision.config is first imported, it will try to load
configuration directory in ~/.provision/secrets.  If it cannot locate
one, it will then try $VIRTUAL_ENV/provision_secrets.
