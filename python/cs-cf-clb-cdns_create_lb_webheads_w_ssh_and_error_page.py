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


# Create a function to take care of the dns record creation
def create_vip_dns(cdnsobj, fqdn, ip_address):

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

            # Check if the record already exists and return it instead
            records = domain.list_records()
            for record in records:
                if record.name == fqdn and record.data == ip_address:
                    print "Record already exists. Skipping"
                    return 0

            # Add record if we made it this far and return from function
            print "Adding record: \n\t" + fqdn + "   IN  A  " + ip_address
            cdnsobj.add_records(domain, recs)
            return 0


# Check for an existing domain
def check_vip_dns(cdnsobj, fqdn):

    # Add the domain record
    domains = cdnsobj.list()
    found_domain = 0
    for domain in domains:
        if fqdn.endswith(domain.name):
            found_domain = 1

    # Bounce if the domain doesn't exist
    if found_domain != 1:
        print "Domain for FQDN of " + fqdn + " doesn't exist for this account."
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
        if image.id == given_image_value or image.name == given_image_value:
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


# Check the public key file and return the dictionary for server creation
def check_pub_key_file(given_filename):

    if os.path.isfile(given_filename):
        print "Public Key File " + given_filename + " exists."
        try:
            pkfile = open(given_filename, 'r')
            content = pkfile.read()
            retfiles = {"/root/.ssh/authorized_keys": content}
            return retfiles
        except IOError as e:
            print "Sorry, but we had trouble opening file " + \
                  given_filename + ". exiting"
            print("({})".format(e))
            sys.exit(1)
    else:
        print "Public key file " + given_filename + " does exist. \
              Please create using a ssh-keygen and run again."


# Check for the error page file and return the contents
def check_error_page_file(given_filename):

    if os.path.isfile(given_filename):
        print "Provided error content file " + given_filename + \
              " exists."
        try:
            errorfile = open(given_filename, 'r')
            content = errorfile.read()
            return content
        except IOError as e:
            print "Sorry, but we had trouble opening file " + \
                  given_filename + ". exiting"
            print("({})".format(e))
            sys.exit(1)
    else:
        print "Error page file " + given_filename + " does exist. \
              Please create run again."


# Create the instance
def create_webhead(csobj, instance_name, flavor_id, image_id, files_dict):

    # Get the server list
    servers = csobj.servers.list()
    for server in servers:
        if server.name == instance_name:
            print "Server by the name of " + instance_name + " already exists."
            return server

    print "Creating new server by the name of " + instance_name
    newserver = csobj.servers.create(instance_name, image_id,
                                     flavor_id, files=files_dict)
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
                    server_data[server_name]['ipaddr'] =  \
                        curserver.accessIPv4
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
        print "Creating lb node for server " + server_name + \
              " on port 80"
        curnode = clbobj.Node(address=cursrv.networks['private'][0],
                              port=80,
                              condition="ENABLED")
        return_nodes.append(curnode)

    print "Returning node list"
    return return_nodes


# Create the load balancer
def create_lb(clbobj, nodes, loadbalancer_name):

    load_balancers = clbobj.list()
    for load_balancer in load_balancers:
        if load_balancer.name == loadbalancer_name:
            print "Found load balancer by the name of " + \
                  loadbalancer_name + ". Skipping creation"
            return load_balancer

    # Create the load balancer for port 80 to the 2 web nodes
    print "Creating an HTTP/80 load balancer called " + \
          loadbalancer_name
    load_balancer_vip = clbobj.VirtualIP(type="PUBLIC")
    load_balancer = clbobj.create(loadbalancer_name,
                                  port=80,
                                  protocol="HTTP",
                                  nodes=nodes,
                                  virtual_ips=[load_balancer_vip])

    return load_balancer


def wait_for_lb(clbobj, load_balancer):
    while 1:
        curlb = clbobj.get(load_balancer.id)
        if curlb.status == 'ACTIVE':
            print "Load Balancer by the name of " + \
                  load_balancer.name + " is active. Done waiting"
            # There seems to be a but in the get function to where
            # all data isn't pulled. Pulling from listing instead.
            load_balancers = clbobj.list()
            for cur_lb in load_balancers:
                if cur_lb.name == load_balancer.name:
                    return cur_lb
        else:
            print "Load Balancer by the name of " + load_balancer.name + \
                  " is in state: " + load_balancer.status + \
                  ".  Waiting 10 seconds"
            time.sleep(10)


# For the exampe, we are just going to use a container
# of 'lb_error_cont' and an object named lb_errorpage
def save_error_page(cfobj, errorpage_content):

    # Check for existing and let the user know if we are
    # creating one or using an existing
    containers = cfobj.list_containers()
    found_container = 0
    for container in containers:
        print container
        if container == 'lb_error_cont':
            print "Found existing container: lb_error_cont"
            found_container = 1
    if not found_container:
        print "Creating container: lb_error_cont"

    # adding and or returning existing container
    contobj = cfobj.create_container("lb_error_cont")

    # Look for and existing error page document
    cont_objects = contobj.get_objects()
    for cont_object in cont_objects:
        if cont_object.name == 'errorpage':
            print "Object of name " + cont_object.name + \
                  " already exists. Using it."
            if cont_object.get() == errorpage_content:
                print "Object content in cloud files for error \
                      page is up to date.  Nothing to do here"
                return 0
            else:
                print "Content doesn't match. Updateing content for \
                      the error page in cloud files."
                contobj.store_object('errorpage', errorpage_content)
                return 0

    # Page doesn't exist so lets create it
    print "Creating errorpage cloud files object and saving content to it"
    contobj.store_object('errorpage', errorpage_content)


def print_server_data(final_server_data, lbobj, vip_fqdn):
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
    print "\tLoad Balancer public vip ip: %s" % (lbobj.virtual_ips[0].address)
    print "\tLoad Balancer public vip fqdn: %s" % (vip_fqdn)


def activate_webservice(server_data):

    for server_name, server_info in sorted(server_data.iteritems()):
        commands = "\"egrep -i -e '(redhat|centos)' /etc/redhat-release; \
                if [ $? == 0 ]; \
                then /usr/bin/yum -y install httpd > /dev/null; \
                /sbin/chkconfig httpd on; \
                /sbin/service httpd start > /dev/null; \
                /sbin/iptables -I INPUT 4 -m state --state NEW \
                -m tcp -p tcp --dport 443 -j ACCEPT; \
                /sbin/iptables -I INPUT 4 -m state --state NEW \
                -m tcp -p tcp --dport 80 -j ACCEPT; \
                /sbin/service iptables save; \
                fi; \
                echo " + server_name + " > /var/www/html/index.html\""
        print "Enabling httpd on server " + server_name
        os.system("ssh -o StrictHostKeyChecking=no root@" +
                  server_info['ipaddr'] + " " + commands +
                  " > /dev/null 2>&1")


# Main function.
def main():

    # Parse the command line arguments
    parser = argparse.ArgumentParser(
        description="Create load balanced webheads with user supplied \
        fqdn and public key for ssh logins with cloud files error page.",
        prog='cs-cf-clb-cdns_create_lb_webheads_w_ssh_and_error_page.py')
    parser.add_argument('--image',
                        help='image id or name (default: CentOS 6.3)',
                        default='CentOS 6.3')
    parser.add_argument('--flavor',
                        help='flavor id or name (default: 512MB Standard\
                        Instance)',
                        default='512MB Standard Instance')
    parser.add_argument('--region',
                        help='Region (default: DFW)',
                        default="DFW")
    parser.add_argument('--webhead_prefix',
                        help='Webhead name prefix (default: \
                        balanced_webhead)',
                        default="balanced_webhead")
    parser.add_argument('--webhead_count',
                        help='Number of webheads (default: 2)',
                        default=2)
    parser.add_argument('--webhead_init',
                        help='Start httpd service on webhead (default: no)',
                        default='no')
    parser.add_argument('--lb_name',
                        help='Load balancer name',
                        required=True)
    parser.add_argument('--fqdn',
                        help='fully qualified domain name',
                        required=True)
    parser.add_argument('--public_keyfile',
                        help='ssh public key file',
                        required=True)
    parser.add_argument('--error_file',
                        help='file containing error page content',
                        required=True)
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

    # Instantiate a clouddns object
    print "Instantiating cloud_dns object"
    cdnsobj = pyrax.cloud_dns

    # Get the flavor id
    flavor_id = get_flavor_from_id_or_name(csobj, args.flavor)

    # Get the image id
    image_id = get_image_from_id_or_name(csobj, args.image)

    # Lets check the domain existance for the fqdn before going on
    check_vip_dns(cdnsobj, args.fqdn)

    # Check public key file
    cs_files = check_pub_key_file(args.public_keyfile)

    # Create the servers by server_count
    for webhead_num in range(1, args.webhead_count + 1):
        webhead_name = "%s%d" % (args.webhead_prefix, webhead_num)
        new_server = create_webhead(csobj, webhead_name, flavor_id,
                                    image_id, cs_files)
        try:
            new_server.adminPass
        except AttributeError:
            print "%s existed, so password can't be pulled" \
                  % (webhead_name)
            server_data[webhead_name] = {
                'password': 'not_available',
                'ipaddr': '0',
                'id': new_server.id}
        else:
            print new_server.adminPass
            server_data[webhead_name] = {
                'password': new_server.adminPass,
                'ipaddr': '0',
                'id': new_server.id}

    # Call function to wait on ip addresses to be assigned
    # and update server_data
    updated_server_data = wait_and_update(csobj, server_data)

    # Create a load balancer nodes
    clbobj = pyrax.cloud_loadbalancers
    new_nodes = create_lb_nodes(clbobj, csobj, updated_server_data)

    # Create the load balancer
    new_lb = create_lb(clbobj, new_nodes, args.lb_name)

    # Wait for load balancer to finish
    updated_lb = wait_for_lb(clbobj, new_lb)

    # Create a DNS entry for the server
    create_vip_dns(cdnsobj, args.fqdn, updated_lb.virtual_ips[0].address)

    # Add a health monitor if needed
    health_monitor = updated_lb.get_health_monitor()
    if not health_monitor:
        print "Health monitor doesn't exist. Creating basic one for httpd"
        updated_lb.add_health_monitor(type="HTTP", delay=10, timeout=10,
                                      attemptsBeforeDeactivation=3,
                                      path="/",
                                      statusRegex="^[234][0-9][0-9]$",
                                      bodyRegex=".*")
    else:
        print "Health monitor exists. Skipping"

    # Wait for load balancer to finish(getting immutable
    # object errors without wait)
    updated_lb = wait_for_lb(clbobj, new_lb)

    # Set the custom content for the error page
    err_content = check_error_page_file(args.error_file)
    epage = updated_lb.get_error_page()
    if epage['errorpage']['content'] != err_content:
        print "Adding custom error page content"
        updated_lb.set_error_page(err_content)
    else:
        print "Custom error content already matches. Skipping \
              setting custom error page"

    # Instantiate a cloudfiles object
    print "Instantiating cloudfiles object"
    cfobj = pyrax.cloudfiles

    # Save the error page to cloud files
    save_error_page(cfobj, err_content)

    # If specified activate httpd on webheads
    if args.webhead_init != "no":
        activate_webservice(updated_server_data)

    # Print the server and lb data
    print_server_data(updated_server_data, updated_lb, args.fqdn)


# Called on execution. We are just going to call the main function from here.
if __name__ == "__main__":
    main()
