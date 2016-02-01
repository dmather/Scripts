#!/usr/bin/env python

###
# Author: Daniel Mather
###

'''
Assumptions of this module:
 - EC2 instances have been marked with a tag key of 'ToSnap' and value of True.
 - EC2 instances are on the us-west-2 region, this can of course be changed.
 - Snapshots older than 2 weeks should be deleted automatically.
 - Sanpshots will be tagged with date to aid in the ability to find the age
   of them.
 - Snapshots will also have a name that consists of the instance name and the
   current date.
'''

import traceback
import boto.ec2
import boto.exception
from boto.exception import EC2ResponseError
from datetime import date, timedelta, datetime
from time import strptime, mktime
import sys

# Create a connection to our servers on us-west-2 (Oregon datacentre)
conn = boto.ec2.connect_to_region('us-west-2')

# Create the backup snapshots for today and tag them.
def create_snapshots_for_today():
    # NOTE: Get all instances with the tag-kay ToSnap (short for to snapshot)
    instances = conn.get_only_instances(filters={'tag-key': 'ToSnap',
                                                 'tag-value': True})
    for instance in instances:
        if 'Name' in instance.tags:
            instanceName = instance.tags['Name']  
            # Iterate all the volumes and find the one with an attachment
            # to the current instance id.
            for volume in conn.get_all_volumes():
                if(volume.attach_data.instance_id == instance.id):
                    cur_date = date.today()
                    date_str = cur_date.strftime("%Y-%m-%d")
                    snapshot_description = "Auto {0} {1} Snapshot".format(
                        instanceName, date_str); 
                    print("Create Automatic Snapshot for {0} on {1}".format(instanceName, date_str))
                    snapshot = volume.create_snapshot(
                        description=snapshot_description,
                        dry_run=False);
                    if snapshot:
                        print("Successful Automatic Snapshot for {0} on {1}".format(instanceName, date_str))
                    snapshot_name = "auto-{0}-{1}-snapshot".format(
                        instanceName, date_str); 
                    snapshot.add_tags({'Name': snapshot_name,
                                        "AutoSnapshot": True,
                                        "Date": date_str})
        else:
            print("Instance {0} has no name tag".format(instance.id));

# Delete snapshots older than 2 weeks.
def delete_old_snapshots():
    # Find the date two weeks ago from today.
    two_weeks_ago = date.today() - timedelta(days=14)
    print("Deleting snapshots that occur before {0}!").format(two_weeks_ago.strftime("%Y-%m-%d"))
    # Search for all snapshots with the tag AutoSnapshot.
    snapshots = conn.get_all_snapshots(filters={'tag-key': 'AutoSnapshot',
                                                'tag-value': True})
    for snapshot in snapshots:
        # Check to make sure that the tag key values that we want to use are
        # actually in the tag keys for each snapshot.
        if 'Name' and 'Date' in snapshot.tags:
            # Date objects can be compared with boolean operators, but it first
            # must be in a non-time tuple format.
            snapshot_date = datetime.fromtimestamp(
		mktime(strptime(snapshot.tags['Date'], "%Y-%m-%d"))).date()
            if(snapshot_date < two_weeks_ago):
                print("Snapshot {0} older than 2 weeks...removing.".format(snapshot.tags['Name']));
                snapshot.delete(dry_run=False)
            else:
                print("Snapshot {0} is newer than 2 weeks".format(snapshot.tags['Name']));
        else:
            print("Snapshot {0} has either no Name or no Date tags".format(snapshot.id));
                    
# Run the create_snapshots_for_today function first, in the event that something
# fails at least we'll try and create new snapshots, but avoid deleting old ones.
try:
    create_snapshots_for_today()
    delete_old_snapshots()
# Agressively match exceptions
except Exception as e:
    print(traceback.format_exc())
    print("Error: {0}".format(e.message))
    print("Not continuing!")
    sys.exit(1)
