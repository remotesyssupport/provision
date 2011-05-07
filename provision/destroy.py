from __future__ import absolute_import
from __future__ import print_function

import sys
import argparse
import xml.dom.minidom

import provision.config as config
import provision.nodelib as nodelib

def parser():
    parser = argparse.ArgumentParser(description='Destroy node by name')
    config.add_auth_args(parser, config)
    parser.add_argument('name')
    parser.add_argument('-t', '--testresults',
                        help='only destroy node if all tests in XML file passed')
    parser.add_argument('-v', '--verbose', default=True)
    return parser

def destroy(parsed):
    driver = nodelib.get_driver(parsed.secret_key, parsed.userid, parsed.provider)
    if nodelib.destroy_by_name(parsed.name, driver):
        return 0
    else:
        print('ERROR: unable to destroy node', file=sys.stderr)
        return 1

def main():
    parsed = config.reconfig(parser)
    if parsed.verbose:
        print('parsed: {0}'.format(parsed))
    if parsed.testresults:
        try:
            dom = xml.dom.minidom.parse(parsed.testresults)
        except:
            print('ERROR: could not parse {0.testresults}, aborting destroy'.format(parsed),
                  file=sys.stderr)
            return 2
        suite = dom.getElementsByTagName('testsuite')[0]
        if int(suite.getAttribute('errors')) != 0 or int(suite.getAttribute('failures')) != 0:
            print('ERROR: not all tests passed, aborting destroy', file=sys.stderr)
            return 3
    return config.handle_errors(destroy, parsed)

if __name__ == '__main__':
    sys.exit(main())
