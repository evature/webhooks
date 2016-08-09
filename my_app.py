# encoding: utf-8
'''
Created on Jul 12, 2016

@author: Tal

Demo implementation of applicative webhooks for the Evature BotKit = http://www.evature.com/docs/botkit.html
It is meant to be as simple as possible.

To achieve max simplicity, it is based on Zappa + Flask, deployed to AWS Lambda.
This is Zappa - https://github.com/Miserlou/Zappa

Assuming you have an AWS account you can have these webhooks running, "serverless", in 5 minutes.
'''
from __future__ import unicode_literals, division
import string
import random

from flask import Flask, request, redirect, render_template, jsonify

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


FLIGHT_STATUS_MESSAGE_EXAMPLE = dict(
    _type='DataMessage',
    subType='airline_update',
    asAttachment=False,
    introMessage='Here is an example of a Flight Status',
    jsonData=dict(
                flight_number='UAL123',
                number=123,
                airline_name='United',
                departure_airport={
                    "airport_code": 'LHR',
                    "city":'London Heathrow',
                    "gate":'232',
                    "terminal":''
                },
                arrival_airport={
                    "airport_code": 'IAD',
                    "city": 'Washington Dulles Intl',
                    "gate": 'C2',
                    "terminal": 'B'
                },
                flight_schedule={
                    "departure_time_actual": "2016-08-09T08:16:00",
                    "arrival_time": "2016-08-09T10:51:00",
                    "departure_time": "2016-08-09T07:30:00",
                    "boarding_time": "",
                }
            ),
    )


BOARDING_PASS_MESSAGE_EXAMPLE = dict(
    _type='DataMessage',
    subType='airline_boardingpass',
    asAttachment=True,
    introMessage='Here is an example of a Boarding Pass',
    jsonData={'auxiliary_fields': [{'label': 'Terminal', 'value': 'T1'},
                                   {'label': 'Departure', 'value': '30OCT 19:05'}],
              'flight_info': {'arrival_airport': {'airport_code': 'AMS', 'city': 'Amsterdam'},
                              'departure_airport': {'airport_code': 'JFK', 'city': 'New York', 'gate': 'D57', 'terminal': 'T1'},
                              'flight_number': 'KL0642',
                              'flight_schedule': {'arrival_time': '2016-01-05T17:30', 'departure_time': '2016-01-02T19:05'}},
              'header_image_url': 'https://d1hz6cg1a1lrv6.cloudfront.net/media/images/evature/logo4-19b0ca62fbf2b08e3bbc9d25298523ea4600422e.jpg',
              'logo_image_url': 'https://d2hbukybm05hyt.cloudfront.net/images/airline_logos/logo_JB.png',
              'passenger_name': 'TAL WEISS',
              'pnr_number': 'CG4X7U',
              'qr_code': 'M1WEISS\\/TAL  CG4X7U nawouehgawgnapwi3jfa0wfh',
              'seat': '75A',
              'secondary_fields': [{'label': 'Boarding', 'value': '18:30'},
                                   {'label': 'Gate', 'value': 'D57'},
                                   {'label': 'Seat', 'value': '75A'},
                                   {'label': 'Sec.Nr.', 'value': '003'}],
              'travel_class': 'business'},
    )


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



@APP.route('/bp', methods=['POST'])
def boarding_pass():
    """Return a boarding pass"""
    response = dict(messages=[BOARDING_PASS_MESSAGE_EXAMPLE],
                    botkitVersion=BOTKIT_API_LATEST_VERSION)
    return jsonify(response)

def random_string(length_of_string):
    """Generate a random string"""
    return ''.join(random.choice(string.ascii_uppercase + string.digits)
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
        response = dict(messages=[BOARDING_PASS_MESSAGE_EXAMPLE],
                        botkitVersion=BOTKIT_API_LATEST_VERSION)
    else:
        response = dict(botkitVersion=BOTKIT_API_LATEST_VERSION,
                        messages=[dict(_type='LoginOAuthEvent',
                                       loginSuccessHook={'webhook': 'flight_boarding_pass'},
                                       text='Please Login in first',
                                       webLoginUrl='https://chat.evature.com/demo_login')])
    return jsonify(response)

@APP.route('/roadside', methods=['POST'])
def roadside():
    """Simple roadside assistance function"""
    response = dict(messages=[
        dict(_type="TextMessage", text="If you need roadside assistance with your Avis vehicle, please call 877-485-5295"),
        dict(_type="ImageMessage",
             imageUrl="http://www.whatafuture.com/wp-content/uploads/2015/03/Google-roadside-assistance-1024x683.jpg")
                                    ],
                    botkitVersion=BOTKIT_API_LATEST_VERSION)
    return jsonify(response)


@APP.route('/flightstat', methods=['POST'])
def flight_status():
    """Simple flight status reply"""
    response = dict(messages=[FLIGHT_STATUS_MESSAGE_EXAMPLE],
                    botkitVersion=BOTKIT_API_LATEST_VERSION)
    return jsonify(response)

# We only need this for local development.
if __name__ == '__main__':
    APP.run()
