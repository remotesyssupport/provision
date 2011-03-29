=========
Provision
=========

Introduction
============

Provision enables users to deploy customized nodes, either via shell
commands, or from a Python program, called as a library.  Building on
Apache Libcloud, which provides a common API for various providers,
Provision allows users to specify, for a new node, which files get
installed, which scripts get run, and which public keys have access,
in a flexible yet repeatable way.

In addition to basic configuration decisions (such as disk image,
size, provider, location, and name), Provision supports four
conceptually distinct components that determine how a node gets
deployed.

1. Public keys that grant their respective private keys root access on
the deployed node.

2. Files that get copied into their specified location on the node.

3. Script templates supporting run time variable substitution that get
run on the node.

4. Minimal Python configuration code for setting secret keys, creating
named bundles of scripts and files for specific functionality, etc.

Provision applications are themselves automatically configured from
the provision/defaults directory and optional, additional
configuration directories which themselves contain an __init__.py
file, and possible subdirectories of files, scripts and public keys.

These additional configuration directories can be used to change the
default configuration parameters in any way, and are typically used to
set secret API keys, access keys, and define site-specific
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

In the following scenarios, it's assumed that there's a
~/.provision/secrets directory which sets the default authentication
credentials.

The following commands are available after installation:

* deploy-node
  Typical usage: $ deploy-node -b dev  
  deploy a node with 'dev' bundle
  
* list-nodes
  Typical usage: $ list-nodes
  print a list of nodes 
  
* destroy-node
  Typical usage: $ deploy-node nodename
  destroy node named 'nodename'
