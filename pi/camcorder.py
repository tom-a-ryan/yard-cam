# USAGE
# python camera.py [--conf conf.json]

from picamera.array import PiRGBArray
from picamera import PiCamera

import argparse
import warnings
import datetime
import imutils
import json
import time
import cv2
import requests

# construct the argument parser and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=False,
    help="path to the JSON configuration file")
args = vars(ap.parse_args())

# filter warnings, load the configuration
# client
warnings.filterwarnings("ignore")
print args["conf"]
conf_file = "conf.json" if args["conf"] is None else args["conf"]
conf = json.load(open(conf_file))
client = None

# initialize the camera and grab a reference to the raw camera capture
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))

# initialize reference times and counters used to throttle frame display and upload rates
lastUploaded = datetime.datetime.now() 
lastDisplayed = None
motionCounter = 0
print "[INFO] warming up...", conf["camera_warmup_time"]
time.sleep(conf["camera_warmup_time"])
print "[INFO] awake now"

avg = None

# capture frames from the camera
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
    # grab the raw NumPy array representing the image and initialize
    # the timestamp and occupied/unoccupied text
    frame = f.array
    timestamp = datetime.datetime.now()
    text = "Unoccupied"

    # resize the frame, convert it to grayscale, and blur it
    frame = imutils.resize(frame, width=500)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)

    # if the average frame is None, initialize it
    if avg is None:
        print "[INFO] starting background model, initialize average."
        avg = gray.copy().astype("float")
        rawCapture.truncate(0)
        continue

    # accumulate the weighted average between the current frame and
    # previous frames, then compute the difference between the current
    # frame and running average
    cv2.accumulateWeighted(gray, avg, 0.5)
    frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

    # threshold the delta image, dilate the thresholded image to fill
    # in holes, then find contours on thresholded image
    thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255,
        cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, None, iterations=2)
    (cnts, _) = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE)

    # loop over the contours
    for c in cnts:
        # if the contour is too small, ignore it
        if cv2.contourArea(c) < conf["min_area"]:
            # print "ignoring contour area", cv2.contourArea(c)
            continue

        # compute the bounding box for the contour, draw it on the frame,
        # and update the text
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = "Occupied"

    # draw the text and timestamp on the frame
    ts = timestamp.strftime("%A %d %B %Y %I:%M:%S %p")
    cv2.putText(frame, "Yard Status: {}".format(text), (10, 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    cv2.putText(frame, ts, (10, frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
        0.35, (0, 0, 255), 1)

    # check to see if the room is occupied
    if text == "Occupied":
        # check to see if enough time has passed between uploads
        if (timestamp - lastUploaded).seconds >= conf["min_upload_seconds"]:
            # increment the motion counter
            motionCounter += 1

            # check to see if the number of frames with consistent motion is
            # high enough
            if motionCounter >= conf["min_motion_frames"]:
                if conf["use_web_upload"] :
                    # filename in ISO 8601 timestamp
                    # TBD fix ambiguous local time, or add (non-standard?) TZ
                    base = timestamp.strftime("%Y-%m-%dT%H:%M:%S")+'.jpg'
                    filename = "{path}/{base}".format( \
                            path=conf["surveillance_images_path"], \
                            base=base)
                    # TBD opener.open() to POST....
                    print "copy to pi file {}".format(filename)
                    rc = cv2.imwrite(filename, frame)
                    print "imwrite return code {}".format(rc)
                    data = {'api' : True,  'reason' : 'upload from pi camera' }
                    files = { 'img' : (filename, open(filename, 'rb')) }
                    url = 'http://hello-ryan-family.appspot.com/upload_image'
                    #url = 'http://requestb.in/1bxnies1'
                    r = requests.post(url, data=data, files=files)
                    print 'status:', r.status_code
                    print 'content', r.content
                # update the last uploaded timestamp and reset the motion
                # counter
                lastUploaded = timestamp
                motionCounter = 0
            else :
                print "motion count {}".format(motionCounter)

    # otherwise, the room is not occupied
    else:
        motionCounter = 0

    # check to see if the frames should be displayed to screen
    if conf["show_video"] :
##        if lastDisplayed is None or \
##        (timestamp - lastDisplayed).seconds >= 1.0/conf["show_video_fps"]:
            # display the security feed
            cv2.imshow("Security Feed", frame)
            lastDisplayed = timestamp
            key = cv2.waitKey(1) & 0xFF

        # if the `q` key is pressed, break from the lop
        # if key == ord("q"):
        #    break

    # clear the stream in preparation for the next frame
    rawCapture.truncate(0)
