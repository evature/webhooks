# encoding: utf-8
'''
Created on Jul 12, 2016

@author: Tal
'''
from __future__ import unicode_literals, division, print_function
import json
import inspect
import string
import random
from datetime import datetime

from flask import Flask, Response, request, redirect, render_template, jsonify

APP = Flask(__name__)

BOTKIT_API_LATEST_VERSION = "0.3.0"

class DataMessageSubType(object):
    """Sub Types of DataMessage JSON data"""
    airline_itinerary = "airline_itinerary"
    airline_checkin = "airline_checkin"
    airline_boardingpass = "airline_boardingpass"
    airline_update = "airline_update"

class BotWebhookTypes(object):
    """The applicative webhooks"""
    search_flight = 'search_flight'
    search_car = 'search_car'
    search_hotel = 'search_hotel' #
    search_cruise = 'search_cruise'
    chat_greeting = 'chat_greeting'
    flight_gate_number = 'flight_gate_number'
    flight_departure_time = 'flight_departure_time'
    flight_arrival_time = 'flight_arrival_time'
    flight_boarding_time = 'flight_boarding_time'
    flight_boarding_pass = 'flight_boarding_pass'
    flight_itinerary = 'flight_itinerary'
    reservation_show = 'reservation_show'
    reservation_cancel = 'reservation_cancel'
    message_logger = 'message_logger' # is activated for every send message used for logging
    flight_status = 'flight_status'
    identify_user = 'identify_user' # activated when the login form is complete - given the form answers and returns the loginData
    identify_user_questions = 'identify_user_questions' # returns custom questions for login - result will be passed to identify_user webhook
    contact_support = 'contact_support'
    airport_navigation = 'airport_navigation'
    change_booking = 'change_booking'
    logout = 'logout'
    arrivals = 'arrivals'
    departures = 'departures'
    show_help = "show_help"
    show_reservation = 'show_reservation'
    ask_time = 'ask_time'
    ask_weather = 'ask_weather'


class Message(object):
    """Base message object to BotIntegration"""
    @property
    def _type(self):
        """Type of the message"""
        return self.__class__.__name__

class TextMessage(Message):
    """A Simple text message container"""
    def __init__(self, text):
        self.text = text

class ImageMessage(Message):
    """An Image message"""
    def __init__(self, imageUrl, asAttachment=False):
        self.imageUrl = imageUrl # pylint:disable=invalid-name
        # asAttachment - if true will send the image as a document attached message (where possible by Messaging Provider)
        self.asAttachment = asAttachment # camelCase on purpose - this becomes a JSON field pylint:disable=invalid-name

class DataMessage(Message):
    """ Data messages contain JSON of specific hook reply,
    eg. https://developers.facebook.com/docs/messenger-platform/send-api-reference/airline-boardingpass-template
    subType constants are in enums.py DataMessageSubType
    """
    def __init__(self, jsonData, subType, asAttachment=False, introMessage=None):
        self.introMessage = introMessage
        self.subType = subType
        self.jsonData = jsonData
        self.asAttachment = asAttachment # in case the message becomes an image, send it as a document attachment or as an inline image


class InteractiveEvent(Message):
    """There can be only one interactive Event - at the end of the messages list"""
    pass

# class LoginOAuthEvent(InteractiveEvent):
#     """ Request OAuth Login:
#     1. Asks the user to press a button to login
#     2. Opens a browser to the webLoginUrl with GET parameters "redirect_url" and timestamped "account_linking_token"
#     3. Once the user completes log in in the website, the user is redirected to the "redirect_url" with the token and "authorization_data"
#     4. The Login is complete - the result is posted  (to loginSuccessHook or loginFailHook)
#     """
#     def __init__(self, webLoginUrl, loginSuccessHook, loginFailHook, text, imageUrl=None):
#         super(LoginOAuthEvent, self).__init__()
#         self.text = text
#         self.imageUrl = imageUrl
#         assert webLoginUrl, "LoginOAuthEvent must include webLoginUrl"
#         self.webLoginUrl = webLoginUrl
#         self.loginSuccessHook = loginSuccessHook
#         self.loginFailHook = loginFailHook

class LoginOAuthEvent(InteractiveEvent):
    """ Request OAuth Login:
    1. Asks the user to press a button to login
    2. Opens a browser to the webLoginUrl with GET parameters "redirect_url" and timestamped "account_linking_token"
    3. Once the user completes log in in the website, the user is redirected to the "redirect_url" with the token and "authorization_data"
    4. The Login is complete - the result is posted  (to loginSuccessHook or loginFailHook)
    """
    def __init__(self, webLoginUrl, loginSuccessHook, text, loginFailHook=None, imageUrl=None):
        super(LoginOAuthEvent, self).__init__()
        self.text = text
        self.imageUrl = imageUrl
        assert webLoginUrl, "LoginOAuthEvent must include webLoginUrl"
        self.webLoginUrl = webLoginUrl
        assert (
                    isinstance(loginSuccessHook, dict) and
                    (loginSuccessHook.get('url') or
                     loginSuccessHook.get('webhook'))
                ), "loginSuccessHook expected to be object with 'url' or 'webhook' key in it"
        self.loginSuccessHook = loginSuccessHook
        self.loginFailHook = loginFailHook

class FilteredObjectEncoder(json.JSONEncoder):
    """Encode Python objects to JSON - only the Truthy values
    Convert to JSON with:   json.dumps(data, cls=FilteredObjectEncoder))"""
    def default(self, obj): # pylint:disable=method-hidden
        if hasattr(obj, "to_json"):
            return self.default(obj.to_json())
        elif isinstance(obj, datetime):
            return '{:%Y-%m-%dT%H:%M:%S}'.format(obj)
        elif hasattr(obj, "__dict__"):
            simple_dict = dict(
                (key, value)
                for key, value in inspect.getmembers(obj)
                if value # only truthy values !
                    and "__" not in key
                    and not inspect.isabstract(value)
                    and not inspect.isbuiltin(value)
                    and not inspect.isfunction(value)
                    and not inspect.isgenerator(value)
                    and not inspect.isgeneratorfunction(value)
                    and not inspect.ismethod(value)
                    and not inspect.ismethoddescriptor(value)
                    and not inspect.isroutine(value)
            )
            return self.default(simple_dict)
        return obj

def messages_to_json(messages, chat_key=None, login_data=None, version=BOTKIT_API_LATEST_VERSION, **kwargs):
    """ Converts list of Message objects to JSON  - for output of WebHook or send_botkit_message url"""
    data = {"botkitVersion": version,
            "messages": messages}
    if chat_key:
        data["chatKey"] = unicode(chat_key)
    if login_data:
        data["loginData"] = login_data
    return json.dumps(data, cls=FilteredObjectEncoder, **kwargs)





@APP.route('/', methods=['POST'])
def index():
    """Main view function"""
    response = messages_to_json([
        TextMessage("Here is your first message"),
        TextMessage("and a second message"),
        ImageMessage("http://www.fortresslockandsecurity.com/wp-content/uploads/2014/04/Austin-Locksmith.png")
                                 ])
    resp = Response(response=response,
                    status=200,
                    mimetype="application/json")
    return resp


@APP.route('/simple', methods=['POST'])
def simple():
    """Simple view function"""
    response = dict(messages=[
        dict(_type="TextMessage", text="Here is your first message"),
        dict(_type="TextMessage", text="and a picture of a lock"),
        dict(_type="ImageMessage",
             imageUrl="http://www.fortresslockandsecurity.com/wp-content/uploads/2014/04/Austin-Locksmith.png")
                                    ],
                    botkitVersion=BOTKIT_API_LATEST_VERSION)
    return jsonify(response)


@APP.route('/human', methods=['POST'])
def human():
    """Transfer to Human function"""
    response = dict(messages=[
        dict(_type="TextMessage", text="I will try to transfer you to an agent!"),
        dict(_type="HandoffToHumanEvent")
                                    ],
                    botkitVersion=BOTKIT_API_LATEST_VERSION)
    return jsonify(response)



@APP.route('/locked', methods=['POST'])
def locked():
    """Simple view function that needs login"""
    body = request.get_json(force=True)
    if body and isinstance(body, dict) and body.get('loginData'):
        response = dict(messages=[
            dict(_type="TextMessage", text="I guess you logged in"),
            dict(_type="TextMessage", text="But you still get a picture of a lock"),
            dict(_type="ImageMessage",
                 imageUrl="http://www.fortresslockandsecurity.com/wp-content/uploads/2014/04/Austin-Locksmith.png")
                                    ],
                        botkitVersion=BOTKIT_API_LATEST_VERSION)
    else:
        response = dict(botkitVersion=BOTKIT_API_LATEST_VERSION,
                        messages=[dict(_type='LoginOAuthEvent',
                                       loginSuccessHook={'webhook': 'flight_boarding_pass'},
                                       text='Please Login in first',
                                       webLoginUrl='https://chat.evature.com/demo_login')])
    return jsonify(response)

def get_boarding_pass(fullname):
    """Generate the data for a boarding pass"""
    boarding_pass_data = {
            "passenger_name": fullname.upper(),
            "pnr_number": "CG4X7U",
            "travel_class": "business",
            "seat": "74J",
            "auxiliary_fields": [
              {
                "label": "Terminal",
                "value": "T1"
              },
              {
                "label": "Departure",
                "value": "30OCT 19:05"
              }
            ],
            "secondary_fields": [
              {
                "label": "Boarding",
                "value": "18:30"
              },
              {
                "label": "Gate",
                "value": "D57"
              },
              {
                "label": "Seat",
                "value": "74J"
              },
              {
                "label": "Sec.Nr.",
                "value": "003"
              }
            ],
            "logo_image_url": "https://d2hbukybm05hyt.cloudfront.net/images/airline_logos/logo_{}.png".format("JB"),
            "header_image_url": "https://d1hz6cg1a1lrv6.cloudfront.net/media/images/evature/logo4-19b0ca62fbf2b08e3bbc9d25298523ea4600422e.jpg",
            "qr_code": r"M1VOLINSKEY\/BARRY  CG4X7U nawouehgawgnapwi3jfa0wfh",
            # "above_bar_code_image_url": "https:\/\/www.example.com\/en\/PLAT.png",
            "flight_info": {
              "flight_number": "KL0642",
              "departure_airport": {
                "airport_code": "JFK",
                "city": "New York",
                "terminal": "T1",
                "gate": "D57"
              },
              "arrival_airport": {
                "airport_code": "AMS",
                "city": "Amsterdam"
              },
              "flight_schedule": {
                "departure_time": "2016-01-02T19:05",
                "arrival_time": "2016-01-05T17:30"
              }
            }
          }
    return boarding_pass_data

@APP.route('/bp', methods=['POST'])
def boarding_pass():
    """Return a boarding pass"""
    boarding_pass_data = get_boarding_pass("Tal Weiss")
    response = messages_to_json([
                                  DataMessage(boarding_pass_data,
                                              subType=DataMessageSubType.airline_boardingpass,
                                              asAttachment=True,
                                              introMessage="Here is an example of a Boarding Pass")
                                 ])
    resp = Response(response=response,
                    status=200,
                    mimetype="application/json")
    return resp

def random_string(length_of_string):
    """Generate a random string"""
    return ''.join(random.choice(string.ascii_uppercase + string.digits) # please no lowercase because Sabre use only uppercase...
                   for _ in range(length_of_string))

@APP.route('/dl', methods=['GET', 'POST'])
def demo_login():
    """Implements a simple page for OAuth login

    # example of URL:
    # https://chat.evature.com/demo_login?
    # account_linking_token=ARREbGIbGD7PQhwWcUt2b5n6yomzPaL6yr_fGAVoFBEADGssklmardZMcnJv9fLsLmpnQ4QuzDhhxg65Ewzq3ObOoUe_aMoDCl5LUS4O_qEumg
    # &redirect_uri=https%3A%2F%2Ffacebook.com%2Fmessenger_platform%2Faccount_linking%2F%3Faccount_linking_token%3DARREbGIbGD7PQhwWcUt2b5n6yomzPaL6yr_fGAVoFBEADGssklmardZMcnJv9fLsLmpnQ4QuzDhhxg65Ewzq3ObOoUe_aMoDCl5LUS4O_qEumg
    """
    messages = []
    context = {}
#     context.update(csrf(request))
    redirect_uri = request.args.get('redirect_uri', '')
    account_linking_token = request.args.get('account_linking_token', '')
    if not redirect_uri:
        messages.append("Expected to find 'redirect_uri' in the query parameters")
    if not account_linking_token:
        messages.append("Expected to find 'account_linking_token' in the query parameters")
    if request.method == 'POST':
        if 'canceled' in request.args:
            # canceled
            messages.append("Canceled!")
            if redirect_uri:
                return redirect(redirect_uri)
        else:
            username = request.form['username']
            password = request.form['password']
            if username.lower().strip() == 'username' and password.lower().strip() == 'password':
                # success
                messages.append("Success!")
                if redirect_uri:
                    return redirect('{}&authorization_code={}'.format(redirect_uri, random_string(5)))
                # https://www.facebook.com/messenger_platform/account_linking/?account_linking_token=ARTXCgVxCwPhsZpxeTmXdAyNJ80epG2CNT1RNFEPXthPcIE8dDpGbIoy7ZRNTu2YsIo-LnGUrXD8mgVXmCq46zuYdua4Pqx0h0N_izSZppv9Vw
                # &authorization_code=PL66J
            else:
                # fail
                messages.append("Invalid Username/Password<br>Use &ldquo;username&rdquo;  and &ldquo;password&rdquo;"
                                "  for succesful login, or click 'cancel'")
    context['message'] = "<br>".join(messages)
    return render_template('demo_login.html', **context)


@APP.route('/bplogin', methods=['POST'])
def flight_boarding_pass_webhook():
    body = request.get_json(force=True)
    if body and isinstance(body, dict) and body.get('loginData'):
        boarding_pass_data = get_boarding_pass("Tal Weiss")
        response = messages_to_json([
                                      DataMessage(boarding_pass_data,
                                                  subType=DataMessageSubType.airline_boardingpass,
                                                  asAttachment=True,
                                                  introMessage="Here is an example of a Boarding Pass")
                                     ])
    else:
        response = messages_to_json([
                                      LoginOAuthEvent(webLoginUrl="https://chat.evature.com/demo_login",
                                                      loginSuccessHook=BotWebhookTypes.flight_boarding_pass,
                                                      loginFailHook=None,
                                                      text="Please Log In first",
                                                      imageUrl=None)
                                     ])

    resp = Response(response=response,
                    status=200,
                    mimetype="application/json")
    return resp

def play():
    """Playing with data"""
    from pprint import pprint
    res1 = messages_to_json([
                                      LoginOAuthEvent(webLoginUrl="https://chat.evature.com/demo_login",
                                                      loginSuccessHook=dict(webhook=BotWebhookTypes.flight_boarding_pass),
                                                      loginFailHook=None,
                                                      text="Please Login in first",
                                                      imageUrl=None)
                                     ])
    pprint(json.loads(res1))


# We only need this for local development.
if __name__ == '__main__':
#     APP.run()
    play()
