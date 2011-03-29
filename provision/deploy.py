from __future__ import absolute_import

import sys
import traceback
import argparse

import provision.config as config
import provision.nodelib as nodelib

def parser():
    parser = argparse.ArgumentParser()
    config.add_auth_args(parser, config)

    # parser.add_argument('subvars', nargs='*',
    #                     help='key=value pairs of script substitution variables')
    parser.add_argument('-b', '--bundles', default=[], action='append')
    parser.add_argument('-d', '--description-file')
    parser.add_argument('-i', '--image', default=config.DEFAULT_IMAGE_NAME)
    parser.add_argument('-l', '--location', default=config.DEFAULT_LOCATION_ID, type=int)
    parser.add_argument('-n', '--name',
                        help='generate randomized name based on prefix if name not specified')
    parser.add_argument('-s', '--size', default=config.DEFAULT_SIZE_ID, type=int)
    parser.add_argument('-t', '--subvars', default=[], action='append',
                        help='key=value pairs of template substitution variables')
    parser.add_argument('-v', '--verbose', default=True)
    parser.add_argument('-x', '--prefix', default=config.DEFAULT_NAME_PREFIX)
    return parser

def main():
    try:
        parsed = config.reconfig(parser)
        deployment = nodelib.Deployment(name=parsed.name, bundles=parsed.bundles,
                                        prefix=parsed.prefix, subvars=parsed.subvars)
        driver = nodelib.get_driver(parsed.secret_key, parsed.userid, parsed.provider)
        node = deployment.deploy(driver, parsed.location, parsed.size, parsed.image)
        if parsed.verbose:
            print(node)
        if parsed.description_file:
            node.write_json(parsed.description_file)
        return sum([sd.exit_status for sd in node.script_deployments])
    except:
        traceback.print_exc(file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())