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
        print "Image with name of " + image_label + " does not exist"
        sys.exit(1)
    return image_id


# Create the instance
def create_server(csobj, instance_name, flavor_id, image_id):

    # Get the server list
    servers = csobj.servers.list()
    for server in servers:
        if server.name == instance_name:
            print "Server by the name of " + instance_name + " already exists."
            return server

    print "Creating new server by the name of " + instance_name
    newserver = csobj.servers.create(instance_name, image_id, flavor_id)
    return newserver


# Create an image from the original server id
def create_image_from_server(csobj, server_id, image_name):

    # Check if an image by that name exists and return it
    images = csobj.images.list()
    for image in images:
        if image.name == image_name:
            print "Image by the name of " + image_name + \
                  " already exists.  Returning it instead \
                  of creating a new one"
            return image

    # If we got this far we still need to create the image
    print "Creating new image by the name of " + image_name
    csobj.servers.create_image(server_id, image_name)

    # Get the new image id and return it
    images = csobj.images.list()
    for image in images:
        if image.name == image_name:
            print "Returning new image by the name of " + image_name
            return image


# Wait for the image to finish saving
def wait_for_active_image(csobj, image_id):

    # Wait until the image status is active
    while 1:
        curimage = csobj.images.get(image_id)
        if curimage.status == 'ACTIVE':
            print "Image by the name of " + curimage.name + \
                  " is now ACTIVE"
            return 0
        else:
            print "Waiting for image by the name of " + curimage.name + \
                  " to finish saving.  Sleeping 60 seconds."
            time.sleep(60)


# Pring out data on the image and clone
def print_server_data(orig_image, cloned_server, password):
    print "\n\n"
    print "###############################"
    print "# Server Information"
    print "###############################\n"

    print "\nServer Image(%s): " % (orig_image.name)
    print "\t%-10s %s \n" % ('cloud id:', orig_image.id)

    print "\nCloned Server(%s): " % (cloned_server.name)
    print "\t%-10s %s " % ('cloud id:', cloned_server.id)
    print "\t%-10s %s " % ('ip addr:', cloned_server.accessIPv4)
    print "\t%-10s %s \n" % ('root pass:', password)


# Main function.
def main():

    # Parse the command line arguments
    parser = argparse.ArgumentParser(
        description="Image a server and create a clone from the image",
        prog='cs_create_image_and_clone_server.py')
    parser.add_argument(
        '--region', help='Region(default: DFW)', default='DFW')
    parser.add_argument(
        '--flavor',
        help='flavor id or name (default: original server flavor)')
    parser.add_argument(
        '--server_name', help='Server name to create image from',
        required=True)
    parser.add_argument(
        '--image_name', help='Name of new image',
        required=True)
    parser.add_argument(
        '--clone_name', help='Name of your new clone created from image',
        required=True)
    args = parser.parse_args()

    # Set the region
    pyrax.set_default_region(args.region)

    # Authenticate using a credentials file: "~/.rackspace_cloud_credentials"
    cred_file = "%s/.rackspace_cloud_credentials" % (os.environ['HOME'])
    print "Setting authentication file to %s" % (cred_file)
    pyrax.set_credential_file(cred_file)

    # Instantiate a cloudservers object
    print "Instantiating cloudservers object"
    csobj = pyrax.cloudservers

    # Get the server id
    servers = csobj.servers.list()
    found = 0
    for server in servers:
        if server.name == args.server_name:
            found = 1
            curserver = server

    if not found:
        print "Server by the name of " + args.server_name + \
              " doesn't exist"
        sys.exit(1)

    # Get the flavor id
    if args.flavor:
        flavor_id = get_flavor_id(csobj, args.flavor)
        print "Using flavor id of " + flavor_id + \
              " from provided arg of " + args.flavor
    else:
        flavor_id = curserver.flavor['id']
        print "Using flavor id of " + flavor_id + " from orig server"

    # Create an image of the original server
    image_obj = create_image_from_server(csobj, curserver.id,
                                         args.image_name)

    # Wait for active image
    wait_for_active_image(csobj, image_obj.id)

    # Create a new server from the image just created
    cloned_server = create_server(csobj, args.clone_name, flavor_id,
                                  image_obj.id)

    # Wait for the server to complete and get data
    print "Wating on clone to finish building\n"
    updated_cloned_server = pyrax.utils.wait_until(cloned_server, "status",
                                                   ["ACTIVE", "ERROR"],
                                                   attempts=0)

    # Print the data
    print_server_data(image_obj, updated_cloned_server,
                      cloned_server.adminPass)


# Called on execution. We are just going to call the main function from here.
if __name__ == "__main__":
    main()
