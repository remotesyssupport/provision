"""This module contains various monkey patches to libcloud libraries
necessary for aws support.

see: http://stackoverflow.com/questions/3765222/monkey-patch-python-class
"""

# Monkey patch libcloud.compute.ssh.ParamikoSSHClient to:
#   accept key filenames in connect()
#   parameterize file open mode in put()

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)s %(levelname)s %(message)s')
logger = logging.getLogger('provision')

def ParamikoSSHClient_connect(self):
    conninfo = {'hostname': self.hostname,
                'port': self.port,
                'username': self.username,
                'allow_agent': False,
                'look_for_keys': False}

    if self.password:
        conninfo['password'] = self.password
    elif self.key:
        conninfo['key_filename'] = self.key
    else:
        raise Exception('must specify either password or key_filename')

    if self.timeout:
        conninfo['timeout'] = self.timeout

    self.client.connect(**conninfo)
    return True

from os.path import split as psplit

def ParamikoSSHClient_put(self, path, contents=None, chmod=None, mode='w'):
    sftp = self.client.open_sftp()
    # less than ideal, but we need to mkdir stuff otherwise file() fails
    head, tail = psplit(path)
    if path[0] == "/":
        sftp.chdir("/")
    for part in head.split("/"):
        if part != "":
            try:
                sftp.mkdir(part)
            except IOError:
                # so, there doesn't seem to be a way to
                # catch EEXIST consistently *sigh*
                pass
            sftp.chdir(part)
    ak = sftp.file(tail, mode=mode)
    ak.write(contents)
    if chmod is not None:
        ak.chmod(chmod)
    ak.close()
    sftp.close()

import libcloud.compute.ssh
libcloud.compute.ssh.ParamikoSSHClient.connect = ParamikoSSHClient_connect
libcloud.compute.ssh.ParamikoSSHClient.put = ParamikoSSHClient_put

# Monkey patch libcloud.compute.drivers.ec2.EC2NodeDriver
import libcloud.compute.drivers.ec2
libcloud.compute.drivers.ec2.EC2NodeDriver.features['create_node'] = ['ssh_keyname']


from libcloud.compute.deployment import Deployment

# Change SSHKeyDeployment to append keys by default (rather than overwrite)

class SSHKeyDeployment(Deployment):
    """
    Installs a public SSH Key onto a host.
    """

    def __init__(self, key):
        """
        @type key: C{str}
        @keyword key: Contents of the public key write
        """
        self.key = self._get_string_value(argument_name='key',
                                          argument_value=key)

    def run(self, node, client):
        """
        Installs SSH key into C{.ssh/authorized_keys}

        See also L{Deployment.run}
        """
        client.put(".ssh/authorized_keys", contents=self.key, mode='a')
        return node


# FileDeployment can be used by all drivers, a general replacement for ex_files param

import os

class FileDeployment(Deployment):
    """
    Install a file.
    """

    def __init__(self, target, source):
        """
        @type target: C{str}
        @keyword target: Location on node to install file

        @type source: C{str}
        @keyword source: Local path of file to be installed
        """
        self.target = target
        self.source = source

    def run(self, node, client):
        """
        Upload the file, retaining permissions

        See also L{Deployment.run}
        """
        perms = os.stat(self.source).st_mode
        client.put(path=self.target, chmod=perms, contents=open(self.source).read())
        return node

import libcloud.compute.deployment
libcloud.compute.deployment.SSHKeyDeployment = SSHKeyDeployment
libcloud.compute.deployment.FileDeployment = FileDeployment


import socket
import time
from libcloud.common.types import LibcloudError
from libcloud.compute.types import NodeState

def NodeDriver_wait_until_running(self, node, wait_period=3, timeout=600):
    """
    Block until node is fully booted and has an IP address assigned.

    @keyword    node: Node instance.
    @type       node: C{Node}

    @keyword    wait_period: Seconds to sleep between each loop iteration
    @type       wait_period: C{int}

    @keyword    timeout: Seconds to wait before timing out
    @type       timeout: C{int}

    @return: C{Node} Node instance on success.
    """

    end = time.time() + timeout

    while time.time() < end:
        nodes = [n for n in self.list_nodes() if n.uuid == node.uuid]

        if len(nodes) == 0:
            raise LibcloudError(value=('Booted node[%s] ' % node
                                + 'is missing from list_nodes.'),
                                driver=self)

        if len(nodes) > 1:
            raise LibcloudError(value=('Booted single node[%s], ' % node
                                + 'but multiple nodes have same UUID'),
                                driver=self)

        node = nodes[0]

        if (node.public_ip is not None
            and node.public_ip != ""
            and node.state == NodeState.RUNNING):
            return node
        else:
            time.sleep(wait_period)
            continue

    raise LibcloudError(value='Timed out after %s seconds' % (timeout),
                        driver=self)


import socket
import time
import traceback

class LoginDisabledError(Exception):
    pass

def NodeDriver_connect_ssh_client(self, ssh_client, wait_period=3, timeout=300):
    """
    Try to connect to the remote SSH server. Each time a connection fails,
    it is retried after wait_period seconds, up to timeout number of seconds.

    @keyword    ssh_client: A configured SSHClient instance
    @type       ssh_client: C{SSHClient}

    @keyword    timeout: Seconds to wait before timing out
    @type       timeout: C{int}

    @return: C{SSHClient} on success
    """
    start = time.time()
    end = start + timeout

    from paramiko.sftp import SFTPError
    while time.time() < end:
        try:
            ssh_client.connect()
            logger.debug('client provisionally connected')
            if 'Please login as the user' in ssh_client.run('pwd')[0]:
                raise LoginDisabledError('%s login disabled' % ssh_client.username)
        except (LoginDisabledError, SFTPError, EOFError, IOError,
                socket.gaierror, socket.error) as e:
            # Retry if a connection is refused or timeout occurred
            # Catch EOFError, for reasons outlined in
            # https://bugs.launchpad.net/paramiko/+bug/567330
            # Catch SFTPError, in case root login not yet
            # re-enabled by user-data script
            logger.exception(traceback.format_exc())
            ssh_client.close()
            time.sleep(wait_period)
            continue
        except:
            logger.exception(traceback.format_exc())
            raise
        else:
            return ssh_client

    raise LibcloudError(value='Could not connect to the remote SSH ' +
                        'server. Giving up.', driver=self)


def NodeDriver_run_deployment_script(self, task, node, ssh_client, max_tries=3):
    """
    Run the deployment script on the provided node. At this point it is
    assumed that SSH connection has already been established.

    @keyword    task: Deployment task to run on the node.
    @type       task: C{Deployment}

    @keyword    node: Node to operate one
    @type       node: C{Node}

    @keyword    ssh_client: A configured and connected SSHClient instance
    @type       ssh_client: C{SSHClient}

    @keyword    max_tries: How many times to retry if a deployment fails
    @type       max_tries: C{int}

    @return:    None on success.
    """
    tries = 0
    while tries < max_tries:
        try:
            node = task.run(node, ssh_client)
        except Exception:
            logger.exception(traceback.format_exc())
            tries += 1
            if tries >= max_tries:
                raise LibcloudError(value='Failed after %d tries'
                                    % (max_tries), driver=self)
            time.sleep(1)
        else:
            ssh_client.close()
            return


import libcloud.compute.base
libcloud.compute.base.NodeDriver.wait_until_running = NodeDriver_wait_until_running
libcloud.compute.base.NodeDriver.connect_ssh_client = NodeDriver_connect_ssh_client
libcloud.compute.base.NodeDriver.run_deployment_script = NodeDriver_run_deployment_script

# class NodeAuthSSHKeyname(object):
#     """
#     An SSH keyname to be installed for authentication to a node.

#     This is the name of a keypair whose public key will normally be
#     added to root's authorized keys on the node, and the path to the
#     local file containing the corresponding private key.


#     >>> from libcloud.compute.base import NodeAuthSSHKeyname
#     >>> k = NodeAuthSSHKeyname('testkey', '~/.ssh/testkey.pem')
#     >>> k
#     <NodeAuthSSHKeyname>
#     """

#     def __init__(self, keyname, path, remote_username='root'):
#         self.keyname = keyname
#         self.path = path
#         self.remote_username = remote_username

#     def __repr__(self):
#         return '<NodeAuthSSHKeyname>'

