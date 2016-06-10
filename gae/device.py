"""`device` abstracts device data along with 'to do' queue per device"""



import logging
import os
import json
import cgi
import urllib



# import Google specific modules
from google.appengine.ext import ndb
from google.appengine.ext import blobstore    # not using blob storage, but are using blob API on GCS (well, that's the plan)

import cloudstorage as gcs  # pip installed into app directoy/lib, not a first class citizen quite yet

# GCS bucket suffix, after app name
APP_DOMAIN = '.appspot.com'             # GAE convention  TBD import from config file throughout *.py


# set up the datastore models

# Device, group's root default = <'Device_list', 'device_list_root'>
#

# used to form a root <kind, id> pair as the ancestor to all devices, the id acys to form a group
# groups could be modelled explcityl, at some poin tthe may need to be.

DEVICE_LIST_KIND="Device_list"                  # the base "model"/"kind" for devices; hardwired here
DEFAULT_DEVICE_LIST_ID="default_device_group"   # (default) Device's ancestor id within bucket

# A parent for all devices.
# Supports multiple non-intersectiong, groups of devices (not further implemented)
def device_list_key(device_list_id = None):
    """Constructs a Device list Datastore key to be used as the ancestor for a group of devices """
    list_key = ndb.Key(ROOT_DEVICE_LIST_KIND, list_id or ROOT_DEVICE_LIST_ID)
    return list_key

# All devices have a 'known' ancestor (serves as a device grouping identifier)
class Device(ndb.Model) :
    """A device, real or virtual """
    external_id = ndb.StringProperty(indexed=True)   # human readable, hopefully unique, identifier, e.g. MAC address
    last_ping_time = ndb.DateTimeProperty(indexed=False)
    # entities should have an ancestor: e.g., device_list_key()
    # implied: ndb Device.id is ssigned by GCS
    # implied: to do queue's added later, Queued items point to devices.

    # return the devices in the specified group
    @classmethod
    def find_devices_in_group(cls, device_list_id = None) :
        ancestor_key = device_list_key(device_list_id)
        return cls.query(ancestor=ancestor_key).order(-cls.last_ping_time)
    
    @classmethod
    # purposefully no default
    def clear_devices(cls, ancestor_key):
        ndb.delete_multi(cls.query(ancestor=ancestor_key).fetch(keys_only=True))
        # and ignore referential integrity issues in To Do Queuesq

    def add_to_do_command(self, **kwargs) :
        ancestor_key = kwargs['ancestor'] if 'ancestor' in kwargs else queue_key()
        cmd = To_Do_Command(
            ancestor = ancestor_key,
            device = kwargs['device'],
            status = 'pending',
            command = kwargs['command'])
        if kwargs['parameters'] :
            cmd.simple_parameters = kwargs['parameters']
        if kwargs['binary'] :
            cmd.binary_parameter = kwargs['binary']
        cmd.put()

    def get_to_do_list(self, device_key) :
        query = To_Do_Queue.query(device=device_key)
        return query
        

QUEUE_KIND = "To_Do_Command"
QUEUE_ROOT_ID = "Command"

def queue_key(queue_group = None) :
    queue_group_key = ndb.key(QUEUE_KIND, queue_group or QUEUE_ROOT_ID)
    """Constructs a command queue Datastore key to be used as the ancestor for a group of commands """
    return queue_group_key

# a set of commands for some device to do
class To_Do_Command(ndb.Model) :
    """A command and optional parametes is added to queue aimed at a device,"""
    device = ndb.KeyProperty(kind=Device, indexed=True)
    queue_time = ndb.DateTimeProperty(auto_now_add=True)  # when added to queue
    status = ndb.StringProperty(indexed=True)
    command = ndb.StringProperty(indexed=False)
    simple_parameters = ndb.StringProperty(indexed=False) # flattened json
    binary_parameter = ndb.BlobProperty()


    @classmethod
    def query_todo_list(cls, ancestor_id = None) :
        """  get to do list """
        ancestor_id = ancestor_if if ancestor_is is not None else ROOT_DEVICE_ID
        ancestor_key = ndb.Key(ROOT_DEVICE_KIND, ancestor_id)
        return cls.query(ancestor=ancestor_key).order(-cls.upload_time)

def device_unit_tests() :
    print "device_unit_test"
    return "seems OK so far :-)"





