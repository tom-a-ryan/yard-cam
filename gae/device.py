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

# Device, group's root default = <'Device_group', 'device_group_root'>
#

# used to form a root <kind, id> pair as the ancestor to all devices, the ids act to form a group
# groups could be modelled explicitly, at some point they may need to be.

DEVICE_GROUP_KIND = "Device_group"                  # the base "model"/"kind" for devices; hardwired here
DEFAULT_DEVICE_GROUP_ID = "default_device_group"    # (default) Device's ancestor id within bucket

# A parent for all devices.
# Supports multiple non-intersectiong, groups of devices (not further implemented)
def device_group_key(device_group_id = None):
    """Constructs a Device group Datastore  key to be used as the ancestor for a group of devices """
    group_key = ndb.Key(DEVICE_GROUP_KIND, device_group_id or DEFAULT_DEVICE_GROUP_ID)
    return group_key

# All devices have a 'known' ancestor (serves as a device grouping identifier)
class Device(ndb.Model) :
    """A device, real or virtual """
    external_id = ndb.StringProperty(indexed=True)   # human readable, hopefully unique, identifier, e.g. MAC address
    last_ping_time = ndb.DateTimeProperty(indexed=True, auto_now_add=True)
    # entities should have an ancestor: e.g., a device_group_key()
    # implied: ndb Device.id is ssigned by GCS
    # implied: to do queue's added later, Queued items point to devices.

    # return the devices in the specified group
    @classmethod
    def find_devices_in_group(cls, device_group_id = None) :
        ancestor_key = device_group_key(device_group_id)
        return cls.query(ancestor=ancestor_key).order(-cls.last_ping_time)
    
    @classmethod
    # purposefully no default id, but whole key required
    def clear_group(cls, device_group_id):
        ancestor_key = device_group_key(device_group_id)
        ndb.delete_multi(cls.query(ancestor=ancestor_key).fetch(keys_only=True))
        # and ignore referential integrity issues in To Do Queuesq

    def add_to_do_command(self, **kwargs) :
        queue_id = kwargs['queue_id'] if 'queue_id' in kwargs else None
        to_do_queue_key = queue_key(queue_id)
        cmd = To_Do_Command(
            parent = to_do_queue_key,
            device = self.key,
            status = 'pending',
            command = kwargs['command'])
        if 'parameters' in kwargs :
            cmd.simple_parameters = kwargs['parameters']
        if 'binary' in kwargs :
            cmd.binary_parameter = kwargs['binary']
        return cmd.put()

    def get_to_do_list(self, device_key) :
        query = To_Do_Queue.query(device=device_key)
        return query

# default <kind, id> ancestor for queue items in ndb
# by convention - the <kind> is stable, vary the ancestor key's id()
QUEUE_KIND = "To_Do_Queue"
DEFAULT_QUEUE_ID = "Commands"

# Note - not using the device as the parent, but entities point back to a device as defined in the Model
# This could be debatable.
# A common Parent, via single queue_id, supports "find all to do" type queries via ancestor.
# the real issue is likely write speeds at scale
# millions of devices may not warrant millions of "to do" writes. 
# not a problem for ~10 camera [TBD async retry code...ha]


def queue_key(queue_id = None) :
    queue_key = ndb.Key(QUEUE_KIND, queue_id or DEFAULT_QUEUE_ID)
    """Constructs a command queue Datastore key to be used as the ancestor for a group of commands """
    return queue_key

# a set of commands for some device to do
class To_Do_Command(ndb.Model) :
    """A command and optional parametes is added to queue aimed at a device,"""
    device = ndb.KeyProperty(kind=Device, indexed=True)
    queue_time = ndb.DateTimeProperty(indexed=True, auto_now_add=True)  # when added to queue
    status = ndb.StringProperty(indexed=True)
    command = ndb.StringProperty(indexed=False)
    simple_parameters = ndb.StringProperty(indexed=False) # flattened json
    binary_parameter = ndb.BlobProperty()

    @classmethod
    def find_commands_in_queue(cls, queue_id = None) :
        """ retrieve all commands with a common ancestor """
        ancestor_key = queue_key(queue_id)
        return cls.query(ancestor=ancestor_key).order(-cls.queue_time)

    @classmethod
    def clear_queue(cls, queue_id = None) :
        ancestor_key = queue_key(queue_id)
        ndb.delete_multi(cls.query(ancestor=ancestor_key).fetch(keys_only=True))        

def unit_test_devices() :
    # Ok, code coverage
    try :
        result = []
        
        default_device_group_key = device_group_key()
        assert default_device_group_key.kind() == DEVICE_GROUP_KIND, "Default device <kind> failure"
        assert default_device_group_key.string_id() == DEFAULT_DEVICE_GROUP_ID, "Default device <id> failure"

        test_device_group_id = "test_devices"
        test_device_group_key = device_group_key(test_device_group_id )
        assert test_device_group_key.string_id() == test_device_group_id , "test device group id failure"

        # this should either work, or be a silent no-op.
        # if it fails to clear, and leaves junk, then remaining results are non-conclusive
        Device.clear_group(test_device_group_id)

        test_device_one = Device(parent=test_device_group_key, external_id="test device one")
        device_one_key = test_device_one.put()

        query = Device.find_devices_in_group(test_device_group_id)

        # assumes fetch() is idempotent
        assert len(query.fetch()) == 1, "expected one test device, but found %d" % len(query.fetch())
        assert query.fetch()[0].key.id() == device_one_key.id(), "test device key put() does not match test device key fetched"

        default_queue_key = queue_key()
        assert default_queue_key.kind() == QUEUE_KIND, "Default Queue kind failure"
        assert default_queue_key.string_id() == DEFAULT_QUEUE_ID, "Default queue id failure"

        test_queue_id = "test_queue"
        test_queue_key = queue_key(test_queue_id)
        assert test_queue_key.kind() == QUEUE_KIND, "test queue kind failure: " + test_queue_key.kind()
        assert test_queue_key.string_id() == test_queue_id, "test queue id failure"

        # silent, untested cleanup...
        print "clear to to", To_Do_Command.clear_queue(test_queue_id)
        
        command_one = To_Do_Command(parent=test_queue_key, device=device_one_key, command="test me")
        command_one_key = command_one.put()

        query = To_Do_Command.find_commands_in_queue(test_queue_id)
        print query
        assert len(query.fetch()) == 1, "expected one test command, but found %d" % len(query.fetch())
        assert query.fetch()[0].key.id() == command_one_key.id(), "test command key put() does not match test command key fetched"

        test_device_two = Device(parent=test_device_group_key, external_id="test device two")
        device_two_key = test_device_two.put()
        command_two_key = test_device_two.add_to_do_command(queue_id=test_queue_id, command="test me too")
        
        
    except AssertionError, error :
        result = error.args[0]
        
    else :
        result = "passed"
    
    return result





