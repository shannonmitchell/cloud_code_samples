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
import time
import pyrax
import argparse


# Main function
def main():

    # Set up the argument parser
    parser = argparse.ArgumentParser(description="Create a cloud database",
                                     prog="cdb_create_cloud_database.py")
    parser.add_argument('--flavor', help="db flavor. def: 512 instance",
                        default="512 instance")
    parser.add_argument('--volume', help="db volume size",
                        default="1")
    parser.add_argument('--label', help="instance label",
                        required=True)
    parser.add_argument('--db_name', help="database name",
                        required=True)
    parser.add_argument('--db_user', help="database user",
                        required=True)
    parser.add_argument('--db_pass', help="database password",
                        required=True)
    args = parser.parse_args()

    # Authenticate using a credentials file: "~/.rackspace_cloud_credentials"
    cred_file = "%s/.rackspace_cloud_credentials" % (os.environ['HOME'])
    print "Setting authentication file to %s" % (cred_file)
    pyrax.set_credential_file(cred_file)

    # Instantiate a clouddns object
    print "Instantiating cloud_dns object"
    cdbobj = pyrax.cloud_databases

    # Check that the instance doesn't already exist and use it if it does
    instances = cdbobj.list()
    inst_exists = 0
    instobj = 0
    for instance in instances:
        if instance.name == args.label:
            print "Instance " + instance.name + " already esists. "
            instobj = instance
            inst_exists = 1

    # Create a new instance if needed.
    if inst_exists == 1:
        print "Using existing instance"
    else:
        # Create the instance
        print "Creating instance by the name of " + args.label
        instobj = cdbobj.create(args.label, args.flavor,
                                volume=args.volume)

    # Looks like we are going to have to wait until its in a proper state.
    is_building = 1
    while is_building:
        instances = cdbobj.list()
        for instance in instances:
            if instance.name == args.label:
                if instance.status != 'ACTIVE':
                    print "Current instance state is: " \
                        + instance.status + ". Waiting 60 seconds"
                    time.sleep(60)
                else:
                    is_building = 0

    # Fetch the updated instance object
    instances = cdbobj.list()
    for instance in instances:
        if instance.name == args.label:
            print "Fetching updated instance: " + instance.name
            instobj = instance

    # Check the database doesn't exist and use it if it does
    databases = instobj.list_databases()
    db_exists = 0
    dbobj = 0
    for database in databases:
        if database.name == args.db_name:
            print "Database " + database.name + " already exists. "
            dbobj = database
            db_exists = 1

    # Create a new database if needed
    if db_exists == 1:
        print "Using existing database"
    else:
        # Create the database
        print "Creating database with the name of " + args.db_name
        dbobj = instobj.create_database(args.db_name)

    # Check the user already exists
    users = instobj.list_users()
    user_exists = 0
    userobj = 0
    if len(users) != 0:
        for user in users:
            if user.name == args.db_user:
                print "User " + user.name + " already exists. "
                userobj = user
                user_exists = 1

    # Create a new user if needed
    if user_exists != 1:
        # Create the user
        print "Creating user with the name of " + args.db_user
        userobj = instobj.create_user(name=args.db_user,
                                      password=args.db_pass,
                                      database_names=[dbobj.name])

    # Print the information
    print "\n## New Instance and DB Info ##"
    print "Instance Name: " + instobj.name
    print "Instance Host: " + instobj.hostname
    print "Database Name: " + dbobj.name
    print "Database User: " + userobj.name
    print "Database Pass: " + args.db_pass
    print "\n"
    print "Example Conn String: \n"
    print "\tmysql -u " + userobj.name + " -p -h " \
          + instobj.hostname + " " + dbobj.name


# Called on execution. We are going to call the main() function
if __name__ == "__main__":
    main()
