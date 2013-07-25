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
import pyrax
import argparse


# Create a function to take care of the dns record creation
def create_server_dns(cdnsobj, fqdn, ip_address):

    # Add the domain record
    domains = cdnsobj.list()
    for domain in domains:
        if fqdn.endswith(domain.name):
            print "Found a matching domain: " + domain.name + \
                  " for fqdn: " + fqdn
            recs = [{'type': 'A',
                     'name': fqdn,
                     'data': ip_address,
                     'ttl': 6000}]
            print "Adding record: \n\t" + fqdn + "   IN  A  " + ip_address
            cdnsobj.add_records(domain, recs)


# Check for an existing domain
def check_server_dns(cdnsobj, fqdn):

    # Add the domain record
    domains = cdnsobj.list()
    found_domain = 0
    for domain in domains:
        if fqdn.endswith(domain.name):
            found_domain = 1

    # Bounce if the domain doesn't exist
    if found_domain != 1:
        print "Domain for FQDN of " + fqdn + " doesn't \
              exist for this account."
        sys.exit(1)


# Get the flavor id from the name
def get_flavor_from_id_or_name(csobj, given_flavor_value):

    flavors = csobj.flavors.list()
    flavor_id = ""
    for flavor in flavors:
        if flavor.id == given_flavor_value \
                or flavor.name == given_flavor_value:
            print "Found flavor with name of \"" + flavor.name + "\""
            flavor_id = flavor.id

    if flavor_id == "":
        print "\nFlavor with name or id of " + given_flavor_value + \
              " does not exist. Please use a flavor id or name from \
              the following available values:\n"
        for flavor in flavors:
            print "id: %s  =>  name: \"%s\"" % (flavor.id, flavor.name)
        sys.exit(1)

    return flavor_id


# Get the image id from the name
def get_image_from_id_or_name(csobj, given_image_value):

    images = csobj.images.list()
    image_id = ""
    for image in images:
        if image.id == given_image_value \
                or image.name == given_image_value:
            print "Found image with name of \"" + image.name + "\""
            image_id = image.id

    if image_id == "":
        print "\nImage with name or id of " + given_image_value + \
              " does not exist. Please use a image id or name from \
              the following available values:\n"
        for image in images:
            print "id: %s  =>  name: \"%s\"" % (image.id, image.name)
        sys.exit(1)

    return image_id


# Create the instance
def create_server(csobj, instance_name, flavor_id, image_id):

    # Get the server list
    servers = csobj.servers.list()
    for server in servers:
        if server.name == instance_name:
            print "Server by the name of " + instance_name + \
                  " already exists. Returning it"
            return server

    print "Creating new server by the name of " + instance_name
    newserver = csobj.servers.create(instance_name, image_id, flavor_id)
    return newserver


def print_server_data(serverobj, curpass):
    print "\n\n"
    print "###############################"
    print "# New Server Information"
    print "###############################\n"
    print "%s(server name and dns entry): " % (serverobj.name)
    print "\t%-10s %s " % ('server id:', serverobj.id)
    print "\t%-10s %s " % ('ip addr:', serverobj.accessIPv4)
    print "\t%-10s %s \n" % ('root pass:', curpass)
    print "\n"
    print "You should be able to get in using the dns entry:  \
            ssh root@" + serverobj.name


# Main function
def main():

    # Parse the command line arguments
    parser = argparse.ArgumentParser(
        description="Create a server based on fqdn, flavor \
        id or name and image id or name.",
        prog='cs-cdns_create_server_with_dns.py')
    parser.add_argument('--fqdn',
                        help='fully qualified domain name',
                        required=True)
    parser.add_argument('--image',
                        help='image id or name',
                        required=True)
    parser.add_argument('--flavor',
                        help='flavor id or name',
                        required=True)
    args = parser.parse_args()

    # Authenticate using a credentials file: "~/.rackspace_cloud_credentials"
    cred_file = "%s/.rackspace_cloud_credentials" % (os.environ['HOME'])
    print "Setting authentication file to %s" % (cred_file)
    pyrax.set_credential_file(cred_file)

    # Instantiate a clouddns object
    print "Instantiating cloud_dns object"
    cdnsobj = pyrax.cloud_dns

    # Instantiate a cloudservers object
    print "Instantiating cloudservers object"
    csobj = pyrax.cloudservers

    # Get the flavor id
    flavor_id = get_flavor_from_id_or_name(csobj, args.flavor)

    # Get the image id
    image_id = get_image_from_id_or_name(csobj, args.image)

    # Lets check the domain existance for the fqdn before going on
    check_server_dns(cdnsobj, args.fqdn)

    # Create the servers by server_count
    new_server = create_server(csobj, args.fqdn, flavor_id, image_id)
    admin_pass = new_server.adminPass

    # Wait for the server to complete and get data
    print "Wating on server to finish building\n"
    updated_server = pyrax.utils.wait_until(new_server, "status",
                                            ["ACTIVE", "ERROR"],
                                            attempts=0)

    # Create a DNS entry for the server
    create_server_dns(cdnsobj, args.fqdn, updated_server.accessIPv4)

    # Print out the results
    print_server_data(updated_server, admin_pass)


# Called on execution. We are going to call the main() function
if __name__ == "__main__":
    main()
