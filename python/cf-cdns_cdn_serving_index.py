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
    parser = argparse.ArgumentParser(description="Create a public cdns \
                                     serving up an index file and adding\
                                     a dns record for it",
                                     prog='cf-cdns_cdn_serving_index.py')
    parser.add_argument('--fqdn',
                        help='fully qualified domain name',
                        required=True)
    parser.add_argument('--container_name', help="name of contianer",
                        required=True)
    parser.add_argument('--index_file', help="file to be used as the index",
                        required=True)
    parser.add_argument('--ttl', help="ttl of cdn files. default: 900",
                        default=900)
    parser.add_argument('--content_type',
                        help="index content type. default: text/html",
                        default="text/html")
    args = parser.parse_args()

    # Authenticate using a credentials file: "~/.rackspace_cloud_credentials"
    cred_file = "%s/.rackspace_cloud_credentials" % (os.environ['HOME'])
    print "Setting authentication file to %s" % (cred_file)
    pyrax.set_credential_file(cred_file)

    # Instantiate a cloudfiles object
    print "Instantiating cloudfiles object"
    cfobj = pyrax.cloudfiles

    # Create the container based on the container_name arg.
    # pyrax returns existing if exists
    print "Creating container: " + args.container_name
    contobj = cfobj.create_container(args.container_name)

    # CDN enable it.
    if contobj.cdn_enabled is True:
        print "Container " + args.container_name + \
              " already public. Skipping"
    else:
        print "Making continer " + args.container_name + " public."
        contobj.make_public(ttl=args.ttl)

    # Pull updated information
    print "Getting updated information for continer " + args.container_name
    contobj = cfobj.get_container(args.container_name)

    # Take the supplied file and upload it
    try:
        content = open(args.index_file).read()
    except IOError:
        print "Error: Can\'t find file or read its data"

    print "Creating index file from provided file and setting\
          content_type of text/html"

    contobj.store_object(os.path.basename(args.index_file),
                         content, content_type=args.content_type)

    # Change the metadata on the container to set an index file
    meta = {'X-Container-Meta-Web-Index': os.path.basename(args.index_file)}
    cfobj.set_container_metadata(contobj, meta)

    # Instantiate a clouddns object
    print "Instantiating cloud_dns object"
    cdnsobj = pyrax.cloud_dns

    # Add the domain cname
    domains = cdnsobj.list()
    for domain in domains:
        if args.fqdn.endswith(domain.name):
            print "Found a matching domain: " + domain.name + \
                  " for fqdn: " + args.fqdn
            cdndomain = contobj.cdn_uri.replace('http://', '')
            recs = [{'type': 'CNAME',
                     'name': args.fqdn,
                     'data': cdndomain,
                     'ttl': args.ttl}]
            print "Adding record: \n\t" + args.fqdn + \
                  "   IN  CNAME  " + cdndomain
            cdnsobj.add_records(domain, recs)

    # Print some info about it
    print "\n\n######################"
    print "# Container Info:"
    print "######################"
    print "\n\tPublic URL: %s\n" % (contobj.cdn_uri)
    print "\tSecure Public URL: %s\n" % (contobj.cdn_ssl_uri)
    print "\tStreaming URL: %s\n" % (contobj.cdn_streaming_uri)
    print "\tMetadata: %s\n" % (cfobj.get_container_metadata(contobj))
    print "\tCNAME: %s => %s\n" % (args.fqdn, cdndomain)


# Called on execution. We are going to call the main() function
if __name__ == "__main__":
    main()
