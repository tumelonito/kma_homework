import datetime as dt
import json
import requests
from flask import Flask, jsonify, request
from google import genai
from google.genai import types

API_TOKEN = "<TOKEN>"
# API key for weather.visualcrossing.com
API_KEY_WEATHER = "<KEY>"
# API key for Google Gemini AI
API_KEY_GENAI = "<KEY>"

app = Flask(__name__)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv



"""
Check if token is valid,
else raises an exception.
"""
def check_token(token: str):
    if token is None:
        raise InvalidUsage("token is required", status_code=400)

    if token != API_TOKEN:
        raise InvalidUsage("wrong API token", status_code=403)


"""
Gets weather data from Weather API for current or specific date.

@param city: City name in ISO format (required)
@type city:  string
@param date: Date for getting weather (yyyy-mm-dd) (optional)
@type date:  string
@return:     Weather data
"""
def get_weather(city: str, date: str):
    # Base url + city name
    url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/" + city

    # if date is given - search weather for such date
    # else - current date
    if date:
        url += "/" + date

    response = requests.get(url, params={'key': API_KEY_WEATHER, 'unitGroup': 'metric'})

    if response.status_code != requests.codes.ok:
        raise InvalidUsage(response.text, status_code=response.status_code)

    response = json.loads(response.text)
    weather = {
        "address": response["address"],
        "datetime": response["days"][0]["datetime"],
        "temp": response["days"][0]["temp"],
        "feelslike": response["days"][0]["feelslike"],
        "conditions": response["days"][0]["conditions"],
    }

    return weather


"""
Generates a playlist in JSON format
for given weather using Gemini API

@param weather: Weather data
@return:        Playlist in JSON format
"""
def get_playlist(weather):
    # Creating a Gemini client
    client = genai.Client(api_key=API_KEY_GENAI)
    # Generates a playlist using Gemini in JSON mode
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Generate a playlist with songs for such weather: {weather}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json"),
    )
    return json.loads(response.text)


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route("/")
def home_page():
    return "<p><h2>KMA Homework1: python Saas.</h2></p>"


@app.route("/content/api/v1/weather_playlist", methods=["POST"])
def current_weather():
    timestamp = dt.datetime.now()
    json_data = request.get_json()

    token = json_data.get("token")
    check_token(token)

    if json_data.get("requester_name"):
        requester_name = json_data.get("requester_name")
    else:
        raise InvalidUsage("requester_name is required", status_code=400)

    if json_data.get("location"):
        location = json_data.get("location")
    else:
        raise InvalidUsage("location is required", status_code=400)

    date = ""
    if json_data.get("date"):
        date = json_data.get("date")

    weather = get_weather(location, date)
    playlist = get_playlist(weather)

    result = {
        "requester_name": requester_name,
        "timestamp": timestamp.isoformat(),
        "location": location,
        "date": weather["datetime"],
        "weather": weather,
        "playlist": playlist,
    }

    return result
