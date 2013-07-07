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
            print "Found flavor with name of " + image_label
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


# Parse through the data structure and print the information
def print_server_data(final_server_data):
    print "\n\n"
    print "###############################"
    print "# New Webhead Information"
    print "###############################\n"
    for server_name, server_info in sorted(final_server_data.iteritems()):
        print "%s: " % (server_name)
        print "\t%-10s %s " % ('cloud id:', server_info['id'])
        print "\t%-10s %s " % ('ip addr:', server_info['ipaddr'])
        print "\t%-10s %s \n" % ('root pass:', server_info['password'])


# Main function.
def main():

    # Parse the command line arguments
    parser = argparse.ArgumentParser(
        description="Create Multiple Webheads",
        prog='cf_create_multiple_webheads.py')
    parser.add_argument(
        '--image', help='image id or name (default: CentOS 6.3)',
        default='CentOS 6.3')
    parser.add_argument(
        '--flavor',
        help='flavor id or name (default: 512MB Standard Instance)',
        default='512MB Standard Instance')
    parser.add_argument(
        '--webhead_count', help='Number of webheads to create(default: 3)',
        default=3)
    parser.add_argument(
        '--webhead_prefix', help='webhead prefix(default: web)',
        default='web')
    parser.add_argument(
        '--region', help='Region(default: DFW)', default='DFW')
    args = parser.parse_args()

    # Set the region
    pyrax.set_default_region(args.region)

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
    flavor_id = get_flavor_id(csobj, args.flavor)

    # Get the image id
    image_id = get_image_id(csobj, args.image)

    # Create the servers by server_count
    for webhead_num in range(1, args.webhead_count + 1):
        webhead_name = "%s%d" % (args.webhead_prefix, webhead_num)
        new_server = create_webhead(csobj, webhead_name, flavor_id, image_id)
        try:
            new_server.adminPass
        except AttributeError:
            print "%s existed, so password can't be pulled" % (webhead_name)
            server_data[webhead_name] = {'password': 'not_available',
                                         'ipaddr': '0',
                                         'id': new_server.id}
        else:
            print new_server.adminPass
            server_data[webhead_name] = {'password': new_server.adminPass,
                                         'ipaddr': '0',
                                         'id': new_server.id}

    # Call function to wait on ip addresses to be assigned and
    # update server_data
    updated_server_data = wait_and_update(csobj, server_data)

    # Print the data
    print_server_data(updated_server_data)


# Called on execution. We are just going to call the main function from here.
if __name__ == "__main__":
    main()
