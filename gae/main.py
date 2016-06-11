"""`main` is the top level module for this Flask application."""

import logging
import os
import json
import cgi
import urllib


# Import the Flask Framework
from flask import Flask
from flask import request, session, g, redirect, url_for, abort, render_template, flash

# import Google specific modules
from google.appengine.api import users
from google.appengine.ext import ndb
from google.appengine.api import app_identity
from google.appengine.ext import blobstore    # not using blob storage, but are using blob API on GCS (well, that's the plan)
from google.appengine.api import images

import cloudstorage as gcs  # pip installed into app directoy/lib, not a first class citizen quite yet

# bring in application support pieces
import device

# GCS bucket suffix, after app name
APP_DOMAIN = '.appspot.com'             # GAE convention
MAX_CONTENT_LENGTH = 8 * 1024 * 1024    # 8 MB max per file uploaded (try to stay in the 'free' billing zone)

# local imports
from private import flask_secret, white_list, admin_name, admin_password # private constants => .gitignore

# set up the datastore models

# used to form a root <kind, id> pair.
ROOT_INCIDENT_KIND="Incident_Log"  # the base "model"/"kind" (pseudo) for everything
ROOT_INCIDENT_ID="My Yard Cam"     # default. Other users or diffferent cameras can create entity groups based on different IDs.

def incident_log_key(incident_id = None):
    """Constructs a Datastore key to be used as the ancestor for entries in an Incident Log """
    key_id = incident_id if incident_id is not None else ROOT_INCIDENT_ID
    root_key = ndb.Key(ROOT_INCIDENT_KIND, key_id)
    ##print "incident root key <", root_key.kind(), root_key.id(), ">"
    return ndb.Key(ROOT_INCIDENT_KIND, key_id)

class Incident(ndb.Model) :
    """An incident is timestamped at the server and points to an image (eventually)"""
    upload_time = ndb.DateTimeProperty(auto_now_add=True)
    reason = ndb.StringProperty(indexed=False)
    image_name = ndb.StringProperty(indexed=False)
    gcs_blob_image_key = ndb.BlobProperty()

    @classmethod
    def logged_entries(cls, ancestor_key):
        return cls.query(ancestor=ancestor_key).order(-cls.upload_time)

    @classmethod
    def clear_log(cls, ancestor_key):
        ndb.delete_multi(cls.query(ancestor=ancestor_key).fetch(keys_only=True))


# helper functions

def verified_user(users) :
    """ verify that a user is logged in to Google with a white-listed email address"""
    user = users.get_current_user()
    logging.info( "check user: {} => {}".format( \
                    user.email() if user else "[No User]", \
                    "OK" if user and user.email() in app.config['WHITE_LIST'] else "Not verified"))
    return user and user.email() in app.config['WHITE_LIST']


# the  main.app enty (<this file>.<this symbol>) in app.yaml gets real work started right about here 
app = Flask(__name__)
app.config.from_object(__name__)            # pulls in UPPER_CASE constants
app.config['SECRET_KEY'] = flask_secret     # Flask's semi secret_key
app.config['WHITE_LIST'] = white_list       # simple list of allowed email accounts (gmail authentication), shpuld move to datasotre
app.config['ADMIN_NAME'] = admin_name       # admin name within this app, not overall GAE admin
app.config['PASSWORD'] = admin_password     # and the admin password

# Basic user flow 
# intermediate access rolls back upstream
#
# --> /hello (main page when unverified) --> /show_entries (main page when verified) --> /admin_login, /admin_logout
#
# --> /upload --> /upload_images note: upload_images is not protected, called from pi,  TODO: fix this
#
# --> /init is direct URL access only, requires /admin_login() 
#
# --> /info is for debugging
#
# --> /rcp --> /rcp_save (saves form input), /rcp_get (gets saved input from/to pi)


@app.route('/')
def hello():
    """Web login and Return a friendly HTTP greeting."""

    # print "at hello"
    # This reaches out to Google, someday general OAUTH, to ensure a valid gmail account is active
    user = users.get_current_user() 
    if not user :
        return redirect(users.create_login_url(request.url))
    print "at hello email is", user.email()
    if user.email() not in app.config['WHITE_LIST'] :
        logging.critical( "Unauthorized access attempt: {}".format(user.email()))
        return 'Sorry, ' + user.nickname() + '. Try logging out and logging in with a permitted gmail address.'
    else:
        return redirect(url_for('show_entries'))

@app.route('/show')
def show_entries():
    if not verified_user(users) :
        return redirect(url_for('hello'))
    
    # "select all" ndb query from default Incident log
    incidents = Incident.logged_entries(incident_log_key())
    entries = [dict(title = incident.reason, 
                    image_name = incident.image_name,
                    image_url = images.get_serving_url(incident.gcs_blob_image_key)) for incident in incidents]
    return render_template('show_entries.html', entries=entries)

@app.route('/upload')
def upload_image_prompt() :
    """ Display a form to find and upload an image"""
    if not verified_user(users) :
        return redirect(url_for('hello'))
    return render_template('upload_image.html')

@app.route('/upload_image', methods=['POST'])
def upload_image() :
    ## TODO - add some security here to limit web-client access to trusted cameras/pi-devices
    image = request.files['img']
    if not image :
        if 'api' in request.form :
            return "Missing Image Data" # to API caller
        else :
            flash("No image file was chosen")
            return redirect(url_for('show_entries'))
    else :
        # desire to store the image in GCS, but using the blob API (not blobstore) so that we can send it back easily
        logging.info("upload _image() source image.filename: {}".format(image.filename))

        # The string value on localhost is 'None', not None 
        bucket_root = app_identity.get_application_id() if app_identity.get_application_id() != "None" else "local"
        gcs_filename = "/{}{}/{}".format(bucket_root, app.config['APP_DOMAIN'], image.filename)
        logging.info("upload_image() destination gcs_filename: {}".format(gcs_filename))
        with gcs.open(gcs_filename, 'w') as f:
            image.save(f)

        reason = request.form['reason'] if 'reason' in request.form else "manually uploaded image"
        logging.info("upload_image() reason: {}".format(reason))
        
        blob_api_filename = '/gs' + gcs_filename 
        logging.info("upload_image() blob_api filename: {}".format(blob_api_filename))
        
        blob_api_key = blobstore.create_gs_key(blob_api_filename)
        logging.info("upload_image() blob_api_key: {}".format(blob_api_key))
                                                                 
        incident = Incident(parent = incident_log_key(),
                            reason = reason,
                            image_name = image.filename,
                            gcs_blob_image_key = blob_api_key)
        i_key = incident.put()
        logging.info("upload_image() added key. kind: {}, id: {}".format(i_key.kind(), i_key.id()))

        url = images.get_serving_url(blob_api_key)
        if 'api' in request.form : 
            return url # to api requestor
        else :
            return redirect(url_for('show_entries'))



@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if not verified_user(users) :
        return redirect(url_for('hello'))
    error = None
    if request.method == 'POST':
        if request.form['admin_name'] != app.config['ADMIN_NAME']:
            error = 'Invalid administrator name'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['admin_logged_in'] = True
            flash('Logged in as administrator')
            return redirect(url_for('show_entries'))
    # on GET, admin verification failure or other errors    
    return render_template('admin_login.html', error=error)

@app.route('/admin_logout')
def admin_logout():
    if not verified_user(users) :
        return redirect(url_for('hello'))
    session.pop('admin_logged_in', None)
    flash('Admin logged out')
    return redirect(url_for('show_entries'))


@app.route('/init')
def init() :
    if not verified_user(users) :
        return redirect(url_for('hello'))
    if not session.get('admin_logged_in') :
        flash("Must be logged in as administrator to re-initialize images.")
        return redirect(url_for('show_entries'))
    else :
        Incident.clear_log(incident_log_key())
        flash('Incident Log Cleared!')
    return redirect(url_for('show_entries'))


@app.route('/rcp')
def rcp_input() :
    """ Display a form to gather remote (to devie) commands and parameters"""
    if not verified_user(users) :
        return redirect(url_for('hello'))
    if not session.get('admin_logged_in') :
        flash("Must be logged in as administrator to use remote commands")
        return redirect(url_for('show_entries'))
    else :
        return render_template('rcp_input.html')

@app.route('/rcp_save', methods=['GET', 'POST'])
def rcp_save() :
    """ From rcp_input form store remote commands and parameters"""
    if not verified_user(users) :
        return redirect(url_for('hello'))
    if not session.get('admin_logged_in') :
        flash("Must be logged in as administrator to use remote commands")
        return redirect(url_for('show_entries'))
    if request.method == 'POST':
        session['rcp'] = {}
        for command in request.form :
            session['rcp'][command] = request.form[command] # 'rcp' : { command1: parameter_value1, command2 : p_v2, ... }
        session['rcp']['sent'] = 0 # retrieval counter
        flash('Remote commands and values queued')
        return redirect(url_for('show_entries'))
    else :
        # could "fail" silently here by jump ingto show_entries, but better to call out the dead end.
        return rcp_get()


@app.route('/rcp_get')
def rcp_get():
    """ no usr verification, return queued paramters """
    if 'rcp' not in session or not isinstance(session['rcp'].get('sent'), int) :
        return json.dumps({})
    else :
        session['rcp']['sent'] += 1
        return json.dumps(session['rcp'])

@app.route('/ping')
def ping() :
    """ pint test from raspberyy pi"""
    return __name__

@app.route('/testd')
def device_test() :
    return device.unit_test_devices()


# only here for general connectivity and health check
# does enforce login and chcks for local (here, not GAE) admin rights.
@app.route('/info')
def info() :
    logging.debug("/info debug check here")
    logging.info("/info info logged here")
    logging.warning("/info warning - you have been warned!")
    logging.error("/info pseudo error here!!")
    logging.critical("/info pseudo critical issue here!!!")
    user = users.get_current_user()
    if user and user.email() in app.config['WHITE_LIST'] :
        if session.get('admin_logged_in') :
            return "Hello {}, you are logged in with administrator privileges".format(user.nickname())
        else :
            return "Hello {}, you are logged in, but without administrator privileges".format(user.nickname())
    else :
        return "Sorry, You are not logged in."


    
@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, in error handler - unexpected error: {}'.format(e), 500
