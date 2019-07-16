# -*- coding: utf- -*-
import boto3
import json
import os
import urllib
from base64 import b64decode
from sleepyq import Sleepyq

# Author: Peter Nealy (panealy@gmail.com)
#
# VERSION       DATE    CHANGES
# Version 0.1   070619  Got initial pass working with SleepIQ
# Version 0.9   071019  Got INFO and MODIFY working enough to be useful
# Version 0.99  071419  Have KMS working to encrypt env variables as well
#                       as the proper NAT and Internet Gatewayt to support
#                       operating out of a VPC.
#
# -----------------------------------------------------------------------------
#
# If you haven't read the README yet, you should :)
#
VERSION = "0.98"

# Note you must set your environment variables in your Lambda function for the
# below to work. It is recommended you encrypt your variables, which will
# require you to configure AWS KMS on your account.
#
# Note that using KMS and the setup it requires (including an internet gateway
# as well as a NAT gateway) is not free. If all you ever do is this lambda 
# function, then it may not be worth it and you may just want to use unencrypted
# ENV variables.
#
# Also note that the decrypted string is byte encoded, so it must be decoded
# as utf-8.
#
# If you'd rather avoid all of the KMS setup, and the slight cost, then simply
# create SNUSER and SNPASS env variables unencrypted, then comment out or delete
# the below 4 lines and replace with:
# USER = os.environ['SNUSER']
# PASS = os.environ['SNPASS']
#
USER_ENCRYPTED = os.environ['SNUSER']
PASS_ENCRYPTED = os.environ['SNPASS']
USER = boto3.client('kms').decrypt(CiphertextBlob=b64decode(USER_ENCRYPTED))['Plaintext'].decode('utf-8')
PASS = boto3.client('kms').decrypt(CiphertextBlob=b64decode(PASS_ENCRYPTED))['Plaintext'].decode('utf-8')

# Don't encrypt this one - it isn't worth it.
ALEXA_SKILL_ID = os.environ['ALEXA_SKILL_ID']

def lambda_handler(event, context):
    # This prevents any other skill from access the LAMBDA function, for added
    # security.
    if (event["session"]["application"]["applicationId"] != ALEXA_SKILL_ID):
        raise ValueError("Invalid Application ID")

    if event["session"]["new"]:
        session_started({"requestId", event["request"]["requestId"]},
                event["session"])

    if event["request"]["type"] == "LaunchRequest":
        return launch_request(event["request"], event["session"])
    elif event["request"]["type"] == "IntentRequest":
        return intent_request(event["request"], event["session"], False)
    elif event["request"]["type"] == "CanFulfillIntentRequest":
        return intent_request(event["request"], event["session"], True)
    elif event["request"]["type"] == "SessionEndedRequest":
        return session_ended_request(event["request"], event["session"])
    else:
        # ... return something to tell say wtf
        raise ValueError("Invalid Intent")

def session_started(session_started_request, session):
    print("Starting new session.")

def session_ended_request(session_ended_request, session):
    print("Ending session.")
    # Cleanup goes here... probably best to consolidate error skill speech
    # here.

def intent_request(request, session, canFulfill):
    print ("Intent Request on %s." % request["timestamp"])

    # NOTE: dialogState is only set if configured for interactive skill
    #dialogState = request["dialogState"]
    dialogState = "STARTED"

    session_attributes = {}
    if dialogState == "STARTED":
        intentName = request["intent"]["name"]
        confirmationStatus = request["intent"]["confirmationStatus"]
        intentSlots = request["intent"]["slots"]

        # INFO - get info about the bed
        # MODIFY - modify sleep number bed settings
        # FIND - find and set new sleep number favorite (unimplemented)
        if intentName == "INFO":
            client = Sleepyq(USER, PASS)
            status = client.login()
            bedId = client.beds()[0].bedId
            fs = client.bed_family_status()[0]
            fav = client.get_favsleepnumber(bedId)
            curLeft = { "sleep_number" : fs.leftSide['sleepNumber'],
                        "in_bed" : fs.leftSide['isInBed'],
                        "fav" : fav.left
                        }
            curRight = { "sleep_number" : fs.rightSide['sleepNumber'],
                         "in_bed" : fs.rightSide['isInBed'],
                         "fav" : fav.right
                         }
            card_title = "Sleep Number Skill - %s" % VERSION

            # This is ugly, but my string manupulation-fu is a bit rusty. I 
            # should clean this up below once things are working.
            speech_output = "Here is your sleep number information for your bed. " + "The left side is set to %d, " % curLeft["sleep_number"] + "and there %s in bed " % ("is someone" if curLeft["in_bed"] else "is no one") + "at this time. The right side is set to %d, and " % curRight["sleep_number"] + "there %s in bed at this time. " % ("is someone" if curRight["in_bed"] else "is no one")
            speech_output += "Your favorites for the left and right side are %d and %d, respectively." % (curLeft['fav'], curRight['fav'])
            reprompt_text = ""

            should_end_session = True
            return build_response(session_attributes, build_speechlet_response(
                card_title, speech_output, reprompt_text, should_end_session))
        elif intentName == "MODIFY":
            card_title = "Sleep Number Skill - %s" % VERSION
            client = Sleepyq(USER, PASS)
            status = False
            try:
                status = client.login()
            except:
                status = False

            if not status:
                # we should bail
                print("LOGIN failed")

            # Get any info we need
            bedId = client.beds()[0].bedId
            settings = {}
            for (name, obj) in iter(intentSlots.items()):
                settings[name] = obj.get('value')

            operation = settings.get('modify_operation')
            if operation == 'fill':
                # If we're being asked to fill, we simply set both sides to 100
                status = False
                for side in ['left', 'right']:
                    status = client.set_sleepnumber(bedId, side, 100)
                    if not status:
                        break
                if status:
                    speech_output = "Successfully filling the bed."
                else:
                    speech_output = "Sorry, I had trouble filling the bed."
            elif operation == 'set':
                # Set sleep number for the specified side
                if not all (k in settings for k in ("side", "setpoint")):
                    speech_output = "Sorry, you must specify both a side " + \
                                    "and set point."
                else:
                    number = None
                    side = settings.get('side')
                    bed = settings.get('bed')
                    if "favorite" in settings['setpoint']:
                        fav = client.get_favsleepnumber(bedId)
                        number = getattr(fav, side)
                    else:
                        # Alexa skill checks for range of 1 to 100 otherwise
                        number = int(settings['setpoint'])
                    if client.set_sleepnumber(bedId, side, number):
                        speech_output = "Setting %s side to %d" % (side, number)
                    else:
                        # something went wrong
                        speech_output = "Sorry. I had trouble setting your " + \
                                        "sleep number."
            elif operation == 'favorite':
                # Set favorite sleep number for the specified side
                if not all (k in settings for k in ("side", "setpoint")):
                    speech_output = "Sorry, you must specify both a side " + \
                                    "and set point."
                else:
                    number = number = int(settings['setpoint'])
                    side = settings.get('side')
                    bed = settings.get('bed')
                    if client.set_favsleepnumber(bedId, side, number):
                        speech_output = "Setting favorite for %s side " + \
                                        "to %d" % (side, number)
                    else:
                        # something went wrong
                        speech_output = "Sorry. I had trouble setting your " + \
                                        "sleep number favorite."
            else:
                speech_output = "Sorry, I'm not sure what you want me to " + \
                                "modify."

            # Build up response
            reprompt_text = ""
            should_end_session = True
            return build_response(session_attributes, build_speechlet_response(
                card_title, speech_output, reprompt_text, should_end_session))
        else:
            # this should drive a dialog, versus just erroring out
            raise ValueError("Invalid intentName")
    elif dialogState == "IN_PROGRESS":
        # NOTE: this isn't in use right now as I don't have dialog enabled

        # continue by using session_attributes from before
        session_attributes = session["session_attributes"]
    elif dialogState == "COMPLETED":
        # NOTE: this isn't in use right now as I don't have dialog enabled
        session_ended_request(request, session)
    else:
        raise ValueError("Invalid dialogState")

def launch_request(event, session):
    session_attributes = {}
    card_title = "Sleep Number Skill - %s" % VERSION
    speech_output = "The Sleep Number™ skill allows you to check the " + \
            "status of your beds, including the current Sleep Number™ " + \
            "setting, as well as request a new setting for your bed."
    reprompt_text = "Try saying asking the me the current bed settings."
    should_end_session = False

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def build_speechlet_response(title, output_text, reprompt_text, should_end_session):
   #imgURL = "https://raw.githubusercontent.com/panealy/aws/master/img/AmazonICO/";   
   # if (!icon) icon = "SleepNumber"; 
   return {
            "outputSpeech": {
                "type": "PlainText",
                "text": output_text
                },
            "card": {
                "type": "Simple",
                "title": title,
                "content": output_text
                },
            "reprompt": {
                "outputSpeech": {
                    "type": "PlainText",
                    "text": reprompt_text
                    }
                },
            "shouldEndSession": should_end_session
    }

def build_response(session_attributes, speechlet_response):
    return {
            "version": "1.0",
            "sessionAttributes": session_attributes,
            "response": speechlet_response
            }
