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
import json
from random import sample

from flask import Flask, request, redirect, render_template, jsonify, make_response
import requests

APP = Flask(__name__)

BOTKIT_API_LATEST_VERSION = "0.4.0"

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
        dict(_type="TextMessage", text="Here is a text message"),
        dict(_type="TextMessage", text="and a picture of a fish"),
        dict(_type="ImageMessage",
             imageUrl="http://pngimg.com/upload/fish_PNG10538.png")
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

@APP.route('/taltesting', methods=['POST'])
def tal_testing():
    """Playground for testing stuff"""
    response = """{
  "botkitVersion": "0.3.0",
  "messages": [
    {
      "_type": "RichMessage",
      "imageUrl": "https://www.travelexinsurance.com/images/default-album/mainimg_flightinsurance.jpg",
      "title": "LHR /u21d2 SVO Option # 1: $1842.24",
      "subtitle": " : 2016-08-31,c: 2016-09-01,one stop at SVO",
      "buttons": [
          {"_type": "ButtonMessage", "text": "Reserve Seat", "url": "https://www.google.com/search?q=flight%20LHR%20to%20SVO"}
      ]
    }
  ]
}"""

    return jsonify(json.loads(response))

@APP.route('/roshan', methods=['POST'])
def for_roshan():
    """Trying to fix the response for Amadeus"""
    response = r"""
{"botkitVersion":"0.3.0","messages":[{"_type":"TextMessage","text":"Here are the the top 3 results:"},{"_type":"MultiRichMessage","messages":[{"_type":"RichMessage","title":"BLR (2016-08-24 18:25) -> NCE (2016-08-24 09:40)","imageUrl":"http://tomcat.www.1aipp.com/sandboxrestservice_chatbot/flight.jpg","buttons":[{"_type":"ButtonMessage","text":"$ 1204.46","url":"https://www.amadeus.net/home/"},{"_type":"ButtonMessage","text":"More Details","url":"https://www.amadeus.net/home/"},{"_type":"ButtonMessage","text":"Book this flight","url":"https://www.amadeus.net/home/"},{"_type":"ButtonMessage","text":"Show similar flights","url":"https://www.amadeus.net/home/"}],"url":"https://www.amadeus.net/home/"},{"_type":"RichMessage","title":"BLR (2016-08-24 18:25) -> NCE (2016-08-24 09:40)","imageUrl":"http://tomcat.www.1aipp.com/sandboxrestservice_chatbot/flight.jpg","buttons":[{"_type":"ButtonMessage","text":"$ 1219.24","url":"https://www.amadeus.net/home/"},{"_type":"ButtonMessage","text":"More Details","url":"https://www.amadeus.net/home/"},{"_type":"ButtonMessage","text":"Book this flight","url":"https://www.amadeus.net/home/"},{"_type":"ButtonMessage","text":"Show similar flights","url":"https://www.amadeus.net/home/"}],"url":"https://www.amadeus.net/home/"},{"_type":"RichMessage","title":"BLR (2016-08-24 17:00) -> NCE (2016-08-24 06:40)","imageUrl":"http://tomcat.www.1aipp.com/sandboxrestservice_chatbot/flight.jpg","buttons":[{"_type":"ButtonMessage","text":"$ 1444.75","url":"https://www.amadeus.net/home/"},{"_type":"ButtonMessage","text":"More Details","url":"https://www.amadeus.net/home/"},{"_type":"ButtonMessage","text":"Book this flight","url":"https://www.amadeus.net/home/"},{"_type":"ButtonMessage","text":"Show similar flights","url":"https://www.amadeus.net/home/"}],"url":"https://www.amadeus.net/home/"}]}]}
"""
    return jsonify(json.loads(response))


@APP.route('/sudhanwa', methods=['POST'])
def for_sudhanwa():
    """Trying to fix the response for Amadeus"""
    response = """
{
  "botkitVersion": "0.3.0",
  "messages": [
    {
      "_type": "TextMessage",
      "text": "Here are the the top 3 results:"
    },
    {
      "_type": "RichMessage",
      "title": "LHR /u21d2 SVO Option # 1: $1842.24",
      "imageUrl": "https://www.travelexinsurance.com/images/default-album/mainimg_flightinsurance.jpg",
      "subtitle": " : 2016-08-31,c: 2016-09-01,one stop at SVO",
      "buttons": [
        {
          "_type": "ButtonMessage",
          "text": "Reserve Seat",
          "payload": null,
          "url": "https://www.google.com/search?q=flight%20LHR%20to%20SVO"
        }
      ]
    },
    {
      "_type": "TextMessage",
      "text": "Outbound Flight"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-08-31T23:35<br><h3>Departs at</h3> :2016-08-31T18:40<br><h3>Fly with</h3> :BA<h3>Airways</h3><br><h3>Origin Airport</h3> :LHR<br><h3>Destination Airport</h3> :HEL<br><h3>Flight Number</h3> :5908<br>"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-09-01T11:05<br><h3>Departs at</h3> :2016-09-01T09:25<br><h3>Fly with</h3> :AY<h3>Airways</h3><br><h3>Origin Airport</h3> :HEL<br><h3>Destination Airport</h3> :SVO<br><h3>Flight Number</h3> :153<br>"
    },
    {
      "_type": "TextMessage",
      "text": "Inbound Flight"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-09-03T20:05<br><h3>Departs at</h3> :2016-09-03T18:20<br><h3>Fly with</h3> :SU<h3>Airways</h3><br><h3>Origin Airport</h3> :SVO<br><h3>Destination Airport</h3> :HEL<br><h3>Flight Number</h3> :6844<br>"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-09-04T09:00<br><h3>Departs at</h3> :2016-09-04T07:45<br><h3>Fly with</h3> :BA<h3>Airways</h3><br><h3>Origin Airport</h3> :HEL<br><h3>Destination Airport</h3> :LHR<br><h3>Flight Number</h3> :5905<br>"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-08-31T23:35<br><h3>Departs at</h3> :2016-08-31T18:40<br><h3>Fly with</h3> :BA<h3>Airways</h3><br><h3>Origin Airport</h3> :LHR<br><h3>Destination Airport</h3> :HEL<br><h3>Flight Number</h3> :5908<br>"
    },
    {
      "_type": "RichMessage",
      "title": "LHR /u21d2 SVO Option # 2: $2110.83",
      "imageUrl": "https://www.travelexinsurance.com/images/default-album/mainimg_flightinsurance.jpg",
      "subtitle": ": 2016-08-31,c: 2016-09-01,one stop at SVO",
      "buttons": [
        {
          "_type": "ButtonMessage",
          "text": "Reserve Seat",
          "payload": null,
          "url": "https://www.google.com/search?q=flight%20LHR%20to%20SVO"
        }
      ]
    },
    {
      "_type": "TextMessage",
      "text": "Outbound Flight"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-08-31T18:05<br><h3>Departs at</h3> :2016-08-31T15:50<br><h3>Fly with</h3> :AF<h3>Airways</h3><br><h3>Origin Airport</h3> :LHR<br><h3>Destination Airport</h3> :CDG<br><h3>Flight Number</h3> :1781<br>"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-09-01T00:10<br><h3>Departs at</h3> :2016-08-31T19:30<br><h3>Fly with</h3> :AF<h3>Airways</h3><br><h3>Origin Airport</h3> :CDG<br><h3>Destination Airport</h3> :SVO<br><h3>Flight Number</h3> :1144<br>"
    },
    {
      "_type": "TextMessage",
      "text": "Inbound Flight"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-09-03T17:00<br><h3>Departs at</h3> :2016-09-03T14:05<br><h3>Fly with</h3> :SU<h3>Airways</h3><br><h3>Origin Airport</h3> :SVO<br><h3>Destination Airport</h3> :CDG<br><h3>Flight Number</h3> :4921<br>"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-09-03T19:20<br><h3>Departs at</h3> :2016-09-03T19:05<br><h3>Fly with</h3> :AF<h3>Airways</h3><br><h3>Origin Airport</h3> :CDG<br><h3>Destination Airport</h3> :LHR<br><h3>Flight Number</h3> :1180<br>"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-08-31T18:05<br><h3>Departs at</h3> :2016-08-31T15:50<br><h3>Fly with</h3> :AF<h3>Airways</h3><br><h3>Origin Airport</h3> :LHR<br><h3>Destination Airport</h3> :CDG<br><h3>Flight Number</h3> :1781<br>"
    },
    {
      "_type": "RichMessage",
      "title": "LHR /u21d2 SVO Option # 3: $2699.13",
      "imageUrl": "https://www.travelexinsurance.com/images/default-album/mainimg_flightinsurance.jpg",
      "subtitle": " : 2016-08-31,c: 2016-09-01,non stop ",
      "buttons": [
        {
          "_type": "ButtonMessage",
          "text": "Reserve Seat",
          "payload": null,
          "url": "https://www.google.com/search?q=flight%20LHR%20to%20SVO"
        }
      ]
    },
    {
      "_type": "TextMessage",
      "text": "Outbound Flight"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-09-01T04:25<br><h3>Departs at</h3> :2016-08-31T22:45<br><h3>Fly with</h3> :SU<h3>Airways</h3><br><h3>Origin Airport</h3> :LHR<br><h3>Destination Airport</h3> :SVO<br><h3>Flight Number</h3> :2585<br>"
    },
    {
      "_type": "TextMessage",
      "text": "Inbound Flight"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-09-03T08:00<br><h3>Departs at</h3> :2016-09-03T06:00<br><h3>Fly with</h3> :SU<h3>Airways</h3><br><h3>Origin Airport</h3> :SVO<br><h3>Destination Airport</h3> :LHR<br><h3>Flight Number</h3> :2570<br>"
    },
    {
      "_type": "HtmlMessage",
      "height": "200",
      "width": "350",
      "html": "<h3>Arrives at</h3> :2016-09-01T04:25<br><h3>Departs at</h3> :2016-08-31T22:45<br><h3>Fly with</h3> :SU<h3>Airways</h3><br><h3>Origin Airport</h3> :LHR<br><h3>Destination Airport</h3> :SVO<br><h3>Flight Number</h3> :2585<br>"
    }
  ]
}
"""

    return jsonify(json.loads(response))




@APP.route('/questions', methods=['POST'])
def questions():
    """Playing with questions"""
    response = """
    {
      "botkitVersion":"0.4.0",
      "messages":[
        {
          "_type":"QuestionnaireEvent",
          "questionnaireAnsweredHook":{
            "webhook":"roadside_assistance",
            "payload":{
              "more_info_to_attach_to_answers":123
            }
          },
          "questionnaireAbortedHook":{
            "webhook":"roadside_assistance",
            "payload":{
              "validation error?":321
            }
          },
          "questions":[
            {
              "_type":"EmailQuestion",
              "name":"email",
              "text":"I need to identify you, what is your email?"
            },
            {
              "_type":"MultiChoiceQuestion",
              "text":"What happened?",
              "name":"what_happened",
              "choices":[
                "Accident",
                "Mechanical problem",
                "Other"
              ]
            },
            {
              "_type":"OpenQuestion",
              "name":"details",
              "text":"I need a string that starts with 'a' and is 3 or more letters",
              "validationRegex":"a.{2}"
            }
          ]
        }
      ]
    }
"""
    return jsonify(json.loads(response))


@APP.route('/greeting', methods=['POST'])
def greeting():
    """Greeting webhook demo implementation"""
    messages = []
    body = request.get_json(force=True)
    first_name = None
    bot_or_agent_key = "bot_or_agent"
    bot_please_reply = "YatraBot Please!"
    if body and isinstance(body, dict):
        bot_or_agent = body.get(bot_or_agent_key)
        if bot_or_agent:
            if bot_or_agent == bot_please_reply:
                messages.append(dict(_type="TextMessage", text="bot requested - how may I help?"))
            else:
                messages.append(dict(_type="TextMessage", text="human requested"))
                messages.append(dict(_type="HandoffToHumanEvent"))
        else:
            user = body.get('user')
            if user and isinstance(user, dict):
                first_name = user.get('firstName')
                if first_name:
                    messages.append(dict(_type="TextMessage", text="Hello there {}!".format(first_name)))
            if not first_name:
                messages.append(dict(_type="TextMessage", text="Hello there!"))
            messages.append(dict(_type="QuestionnaireEvent",
                                 questionnaireAnsweredHook=dict(webhook="chat_greeting", payload=dict()),
                                 questions=[dict(_type="MultiChoiceQuestion",
                                                 text="Would you like to talk to YatraBot or wait for an agent?",
                                                 name=bot_or_agent_key,
                                                 choices=["YatraBot Please!",
                                                          "Wait for an agent"])]))
    response = dict(messages=messages, botkitVersion=BOTKIT_API_LATEST_VERSION)
    return jsonify(response)



@APP.route('/https_proxy', methods=['GET'])
def https_proxy():
    """Trying to fix the response for Amadeus"""
    url = request.args.get('url')
    if url:
        unquoted_url = requests.utils.unquote(url)
        try:
            res = requests.get(unquoted_url)
        except requests.exceptions.RequestException:
            pass
        else:
            response = make_response(res.content)
            for key, value in res.headers.iteritems():
                response.headers[key] = value
            return response
    return "No URL"

AIRPORT_SUGGESTIONS = [
    ("Flight Status:",
     ["My flight status",
      "status of ua-123",
      "arrivals",
      "display arrivals",
      "departures",
      "list arriving flight",
      "departure list",
      "departures flights",
      ]),
    ("General questions:",
     ["Time in Rome",
      "the weather in paris",
      "Who are you?",
      "What are you?",
      "Who made you?",
      "What do you eat?",
      "What's new?",
      "Who am I?",
      "Where are you from?",
      "What is your name?",
      ]),
    ("Hotel searches:",
     ["hotel tonight",
      "cheap hotel nyc",
      "3-4 stars for Monday",
      ]),
    ("Reach out for some help:",
     ["customer service",
      "call support",
      "talk to a human?",
      "help",
      'information',
      'help me',
      'can you help me?',
      "can u show me info?",
      "I need assistance",
      ]),
    ("Request personal information:",
     ["departure time?",
      "boarding pass",
      "When do I depart?",
      "Show arrival time",
      "When do I arrive?",
      "When are we boarding?",
      "Display my itinerary",
      "Trip details",
      "Number of my gate",
#     "12345678901234567890",
    ]),
]

@APP.route('/capabilities_evature_airports', methods=['POST'])
def capabilities_evature_airports():
    """Capabilities view function"""
    messages = [dict(_type="TextMessage", text="I can do many things! Here are a few options:")]
    categories = sample(AIRPORT_SUGGESTIONS, 3)
    multi_rich_messages = []
    for category in categories:
        buttons = [dict(_type="ButtonMessage", text=text, action=dict(_type="InputTextAction", inputText=text))
                   for text in sample(category[1], 3)] # pylint:disable=unsubscriptable-object
        message = dict(_type="RichMessage", title=category[0], buttons=buttons) # pylint:disable=unsubscriptable-object
        multi_rich_messages.append(message)
    messages.append(dict(_type="MultiRichMessage", messages=multi_rich_messages))
    response = dict(botkitVersion=BOTKIT_API_LATEST_VERSION, messages=messages)
    return jsonify(response)



# We only need this for local development.
if __name__ == '__main__':
    APP.run()

