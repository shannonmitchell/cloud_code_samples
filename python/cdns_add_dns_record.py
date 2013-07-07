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
import pyrax
import argparse


# Main function
def main():

    # Parse the command line arguments
    parser = argparse.ArgumentParser(description="Add a dns A record",
                                     prog='cdns_add_dns_record.py')
    parser.add_argument('--fqdn', help='fully qualified domain name',
                        required=True)
    parser.add_argument('--ip', help='ip address', required=True)
    args = parser.parse_args()

    # Authenticate using a credentials file: "~/.rackspace_cloud_credentials"
    cred_file = "%s/.rackspace_cloud_credentials" % (os.environ['HOME'])
    print "Setting authentication file to %s" % (cred_file)
    pyrax.set_credential_file(cred_file)

    # Instantiate a clouddns object
    print "Instantiating cloud_dns object"
    cdnsobj = pyrax.cloud_dns

    # Add the domain record
    domains = cdnsobj.list()
    for domain in domains:
        if args.fqdn.endswith(domain.name):
            print "Found a matching domain: " + domain.name + \
                  " for fqdn: " + args.fqdn
            recs = [{'type': 'A', 'name': args.fqdn, 'data': args.ip,
                     'ttl': 6000}]
            print "Adding record: \n\t" + args.fqdn + "   IN  A  " + args.ip
            cdnsobj.add_records(domain, recs)

# Called on execution. We are going to call the main() function
if __name__ == "__main__":
    main()
