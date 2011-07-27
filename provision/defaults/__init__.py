def init(config):
    # Override the following defaults in a local configuration dir
    # e.g. ~/.provision/secrets/__init__.py
    config.DEFAULT_PROVIDER = None # e.g. "rackspace"
    config.DEFAULT_USERID = None
    config.DEFAULT_SECRET_KEY = None

    config.add_bundle('bootstrap-python', ['bootstrap-python.sh'])
    config.add_bundle('dev', ['emacs.sh', 'screen.sh'],
                      ['/root/.emacs.d/init.el', '/root/.screenrc'])
    config.add_bundle('hudson', ['jre.sh', 'postfix.sh', 'hudson.sh'])
    config.add_bundle('libcloud', ['libcloud-env.sh'])
    config.add_bundle('mta', ['postfix.sh'])
    config.add_bundle('nginx', ['nginx.sh'])
    config.add_bundle('pyenv', ['python-env.sh'])
    config.add_bundle('proxy',['apache-proxy.sh'])
    config.add_bundle('snmpd', ['snmpd.sh'])
    config.add_bundle('tz', ['tz.sh'])
    config.add_bundle('zenoss',['zenoss.sh'])
