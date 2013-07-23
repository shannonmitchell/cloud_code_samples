#!/usr/bin/env python

# Copyright 2013 Rackspace
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHO
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. Seethe
#    License for the specific language governing permissions and limitations
#    under the License.
#

import os
import sys
import time
import pyrax
import argparse


# Get the flavor id from the label
def get_flavor_id(csobj, flavor_label):

    flavors = csobj.flavors.list()
    flavor_id = ""
    for flavor in flavors:
        if flavor.name == flavor_label:
            print "Found flavor with name of " + flavor_label
            flavor_id = flavor.id
    if flavor_id == "":
        print "Flavor with name of " + flavor_label + " does not exist."
        sys.exit(1)
    return flavor_id


# Get the image id from the label
def get_image_id(csobj, image_label):

    images = csobj.images.list()
    image_id = ""
    for image in images:
        if image.name == image_label:
            print "Found image with name of " + image_label
            image_id = image.id
    if image_id == "":
        print "Image with name of " + image_label + "does not exist."
        sys.exit(1)
    return image_id


# Create the instance
def create_webhead(csobj, instance_name, flavor_id, image_id):

    # Get the server list
    servers = csobj.servers.list()
    for server in servers:
        if server.name == instance_name:
            print "Server by the name of " + instance_name + " already exists."
            return server

    print "Creating new server by the name of " + instance_name
    newserver = csobj.servers.create(instance_name, image_id, flavor_id)
    return newserver


# Wait for created servers to have ip info and return the populated data
def wait_and_update(csobj, server_data):

    # Keep looping till we have them all
    completed = 0
    while 1:
        completed = 1
        # Loop through the server data and update.
        for server_name, server_info in server_data.iteritems():
            if server_info['ipaddr'] == '0':
                curserver = csobj.servers.get(server_info['id'])
                if curserver.accessIPv4:
                    print "Found access ip: " + curserver.accessIPv4
                    server_data[server_name]['ipaddr'] = curserver.accessIPv4
                else:
                    completed = 0

        if completed == 1:
            return server_data
        else:
            print "Waiting for access IPs to be assigned. Sleeping 60 seconds."
            time.sleep(60)


# Create nodes for the load balancer
def create_lb_nodes(clbobj, csobj, final_server_data):
    return_nodes = []
    for server_name, server_info in final_server_data.iteritems():
        cursrv = csobj.servers.get(server_info['id'])
        print "Creating lb node for server " + server_name + " on port 80"
        curnode = clbobj.Node(address=cursrv.networks['private'][0],
                              port=80, condition="ENABLED")
        return_nodes.append(curnode)

    print "Returning node list"
    return return_nodes


# Create the load balancer
def create_lb(clbobj, nodes, lb_name):

    load_balancers = clbobj.list()
    for load_balancer in load_balancers:
        if load_balancer.name == lb_name:
            print "Found load balancer by the name of " + lb_name + \
                  ". Skipping creation"
            return load_balancer

    # Create the load balancer for port 80 to the 2 web nodes
    print "Creating an HTTP/80 load balancer called " + lb_name
    load_balancer_vip = clbobj.VirtualIP(type="PUBLIC")
    load_balancer = clbobj.create(lb_name, port=80,
                                  protocol="HTTP", nodes=nodes,
                                  virtual_ips=[load_balancer_vip])

    return load_balancer


def wait_for_lb(clbobj, load_balancer):
    while 1:
        curlb = clbobj.get(load_balancer.id)
        if curlb.status == 'ACTIVE':
            print "Load Balancer by the name of " + \
                  load_balancer.name + " is active. Done waiting"
            # There seems to be a problem in the get function to
            # where all data isn't pulled. Pulling from listing instead.
            load_balancers = clbobj.list()
            for cur_lb in load_balancers:
                if cur_lb.name == load_balancer.name:
                    return cur_lb
        else:
            print "Load Balancer by the name of " + load_balancer.name + \
                  " is in state: " + load_balancer.status + \
                  ".  Waiting 10 seconds"
            time.sleep(10)


def print_server_data(final_server_data, lbobj):
    print "\n\n"
    print "###############################"
    print "# New LB/Webhead Information"
    print "###############################\n"
    for server_name, server_info in sorted(final_server_data.iteritems()):
        print "%s: " % (server_name)
        print "\t%-10s %s " % ('cloud id:', server_info['id'])
        print "\t%-10s %s " % ('ip addr:', server_info['ipaddr'])
        print "\t%-10s %s \n" % ('root pass:', server_info['password'])

    print "Load Balancer Name: %s" % (lbobj.name)
    print "\tLoad Balancer port: %s" % (lbobj.port)
    print "\tLoad Balancer node count: %s" % (lbobj.nodeCount)
    print "\tLoad Balancer protocol: %s" % (lbobj.protocol)
    print "\tLoad Balancer public ip: %s" % (lbobj.virtual_ips[0].address)


# Main function.
def main():

    # Parse the command arguments
    parser = argparse.ArgumentParser(description="Create load balancer and \
                                     webheads setting behind it",
                                     prog="clb-cs_create_nodes_behind_load_\
                                     balancer.py")
    parser.add_argument('--region',
                        help="(DFW, ORD, SYD) def: DFW", default="DFW")
    parser.add_argument('--webhead_prefix',
                        help="Prefix name for webhead. default: webhead",
                        default="webhead")
    parser.add_argument('--webhead_count',
                        help="Number of webheads. default: 2",
                        default=2)
    parser.add_argument('--webhead_flavor',
                        help="Webhead flavor. default: '512MB Standard \
                        Instance'", default="512MB Standard Instance")
    parser.add_argument('--webhead_image',
                        help="Webhead image. default: 'CentOS 6.3'",
                        default="CentOS 6.3")
    parser.add_argument('--lb_name', help="Load Balancer Name", required=True)
    args = parser.parse_args()

    # Server Data Dictionary
    server_data = dict()

    # Authenticate using a credentials file: "~/.rackspace_cloud_credentials"
    cred_file = "%s/.rackspace_cloud_credentials" % (os.environ['HOME'])
    print "Setting authentication file to %s" % (cred_file)
    pyrax.set_credential_file(cred_file)

    # Instantiate a cloudservers object
    print "Instantiating cloudservers object"
    csobj = pyrax.cloudservers

    # Get the flavor id
    flavor_id = get_flavor_id(csobj, args.webhead_flavor)

    # Get the image id
    image_id = get_image_id(csobj, args.webhead_image)

    # Create the servers by server_count
    for webhead_num in range(1, args.webhead_count + 1):
        webhead_name = "%s%d" % (args.webhead_prefix, webhead_num)
        new_server = create_webhead(csobj, webhead_name, flavor_id, image_id)
        try:
            new_server.adminPass
        except AttributeError:
            print "%s existed, so password can't be pulled" % (webhead_name)
            server_data[webhead_name] = {'password': 'not_available',
                                         'ipaddr': '0', 'id': new_server.id}
        else:
            print new_server.adminPass
            server_data[webhead_name] = {'password': new_server.adminPass,
                                         'ipaddr': '0', 'id': new_server.id}

    # Call function to wait on ip addresses to be assigned and
    # update server_data
    updated_server_data = wait_and_update(csobj, server_data)

    # Create a load balancer nodes
    clbobj = pyrax.cloud_loadbalancers
    new_nodes = create_lb_nodes(clbobj, csobj, updated_server_data)

    # Create the load balancer
    new_lb = create_lb(clbobj, new_nodes, args.lb_name)

    # Wait for load balancer to finish
    updated_lb = wait_for_lb(clbobj, new_lb)

    # Print the server and lb data
    print_server_data(updated_server_data, updated_lb)


# Called on execution. We are just going to call the main function from here.
if __name__ == "__main__":
    main()
