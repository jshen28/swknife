#!/usr/bin/env python
# -*- coding: utf-8 -*-


import logging
import os

import eventlet
import urllib3
from keystoneauth1 import session, loading
from neutronclient.v2_0 import client

# disable ssl verification warning
urllib3.disable_warnings()

eventlet.monkey_patch()

DEFAULT_SPEC = "general"
LOGGER = None
COLUME_NAME = ["service", "network_name", "subnet_name", "cidr", "ip_pool", "vlanid", "disable_dhcp", 'disable_gw',
               'gw', 'dns', 'host_routes']
MAX_COLUMNS = len(COLUME_NAME)
DEFAULT_NIC = "physnet1"


def get_logger():
    global LOGGER
    if not LOGGER:
        LOGGER = logging.getLogger(__name__)
    return LOGGER


def setup_logging(debug=False):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)


def create_networks(neutron_client, networks):
    """
    create all required flavors
    :param neutron_client
    :param networks
    :return:
    """

    success = []

    if not neutron_client:
        raise Exception("neutron client has not been properly setup!")

    logger = get_logger()

    for network in networks:
        logger.info("create network %s", str(network))
        try:
            network.create_network(neutron_client)
            logger.info('successfully create network:subnet %s:%s', network.network_name, network.subnet_name)
            success.append(network)
        except Exception as e:
            logger.error("create network:subnet %s:%s failed, %s", network.network_name, network.subnet_name, e)

            # break on exception
            break

    return success


def clean_networks(networks, client):
    logger = get_logger()
    for i in networks:
        network_id = i.get('network_id')
        logger.info('clean network: %s', network_id)
        client.delete_network(network_id)


def init_neutron_client(credentials):
    # get logger
    logger = get_logger()

    # relation between variable name & corresponding environment variable
    required_fields = {'auth_url': 'OS_AUTH_URL',
                       'username': "OS_USERNAME",
                       'password': 'OS_PASSWORD',
                       'user_domain_name': "OS_USER_DOMAIN_NAME",
                       'project_name': "OS_PROJECT_NAME",
                       'project_domain_name': "OS_PROJECT_DOMAIN_NAME"
                       }

    # check & pop values from environment variable
    options = {}
    for key in required_fields.keys():
        if not credentials.get(key):
            value = os.environ[required_fields[key]]
            if not value:
                raise Exception("%s(%s) is missing" % (key, required_fields[key]))
            options.update({key: value})
        else:
            options.update({key: credentials.get(key)})

    logger.info("begin initializing nova client")
    loader = loading.get_plugin_loader('v3password')
    auth = loader.load_from_options(**options)
    sess = session.Session(auth=auth, verify=False)

    # fixme fix this ugle code!!
    endpoint_type = credentials.get('endpoint_type', os.environ['OS_ENDPOINT_TYPE'])
    endpoint_type = endpoint_type if endpoint_type else "public"
    region_name = credentials.get('region_name', os.environ['OS_REGION_NAME'])
    region_name = region_name if region_name else "RegionOne"

    nova_client = client.Client(session=sess, endpoint_type=endpoint_type, region_name=region_name)
    logger.info("initialzing neutron client completed successfully")

    # return a glance client
    return nova_client


def get_parser():
    import argparse

    parser = argparse.ArgumentParser(description='generate required flavors')
    parser.add_argument('-d', '--debug', dest='debug', action='store_const', const=True,
                        default=False, help='enable debugging')
    parser.add_argument('-o', '--ouput', dest='output_file', default="networks.xls", help='write output to file')
    parser.add_argument('-c', '--count', dest='count', default=3, type=int, help='number of networks to be created')
    parser.add_argument('--observe', dest='observe', default=False, action='store_const', const=True)
    parser.add_argument('-f', '--file', dest='file', default="result.json",
                        help='save successfully created network to file')
    parser.add_argument('--clean', dest='clean', default=False, action='store_const', const=True,
                        help='clean previous result')

    return parser.parse_args()


def main():
    parser = get_parser()

    # setup loggings
    setup_logging(debug=parser.debug)

    # assemble flavor objects
    logger = get_logger()

    # init neutorn client
    neutron_client = init_neutron_client({})

    def get_ports_by_net_id(net_id):
        params = {
            "network_id": net_id,
            "device_owner": "compute:%s" % os.environ['OS_AVAILABILITY_ZONE']
        }
        ports = neutron_client.list_ports(**params).get('ports', [])
        return ports

    networks = neutron_client.list_networks()['networks']
    net_ids = [i['id'] for i in networks]
    gp = eventlet.GreenPool(size=10)
    for i in gp.imap(get_ports_by_net_id, net_ids):
        print i

    return 0


if __name__ == "__main__":
    exit(main())
