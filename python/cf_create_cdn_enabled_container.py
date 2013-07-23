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

    # Parse the arguments
    parser = argparse.ArgumentParser(description="Create a named cloud files \
                                     contaner and CDN enable it",
                                     prog="cf_create_cdn_enabled_container.py")
    parser.add_argument('--name', help="conainter name", required=True)
    parser.add_argument('--cdn_ttl', help="Time to live for cdn pages. def: \
                        900", default=900)
    args = parser.parse_args()

    # Authenticate using a credentials file: "~/.rackspace_cloud_credentials"
    cred_file = "%s/.rackspace_cloud_credentials" % (os.environ['HOME'])
    print "Setting authentication file to %s" % (cred_file)
    pyrax.set_credential_file(cred_file)

    # Instantiate a cloudfiles object
    print "Instantiating cloudfiles object"
    cfobj = pyrax.cloudfiles

    # Create the container if it doesn't exist
    # pyrax returns existing if exists
    print "Creating container: " + args.name
    contobj = cfobj.create_container(args.name)

    # CDN enable it.
    if contobj.cdn_enabled is True:
        print "Container " + args.name + " already public. Skipping"
    else:
        print "Making continer " + args.name + " public."
        contobj.make_public(ttl=args.cdn_ttl)

    # Pull updated information
    print "Getting updated information for continer " + args.name
    contobj = cfobj.get_container(args.name)

    # Print some info about it
    print "######################"
    print "# Container Info:"
    print "######################"
    print "\n\tPublic URL: %s\n" % (contobj.cdn_uri)
    print "\tSecure Public URL: %s\n" % (contobj.cdn_ssl_uri)
    print "\tStreaming URL: %s\n" % (contobj.cdn_streaming_uri)


# Called on execution. We are going to call the main() function
if __name__ == "__main__":
    main()
