from   __future__   import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse

import os
import traceback

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.renderers import JSONRenderer
from rest_framework import authentication, permissions

import requests
import after_response
import regex

import xml.etree.ElementTree as ET

from cacheutils import cacheutils
from aiengines import aiwitutils
from weatherengines import openweathermaputils


# wit access token
_WIT_TOKEN = os.environ["WIT_TOKEN"]
assert _WIT_TOKEN, "No WIT_TOKEN set"
# openweathermap access token
_OPENWEATHERMAP_TOKEN = os.environ["OPENWEATHERMAP_TOKEN"]
assert _OPENWEATHERMAP_TOKEN, "No OPENWEATHERMAP_TOKEN is set"
# openweathermap language
_OPENWEATHERMAP_LANG = os.environ.get("OPENWEATHERMAP_LANG", "")
# openweathermap units
_OPENWEATHERMAP_UNITS = os.environ.get("OPENWEATHERMAP_UNITS", "")
# openweathermap home city ID
_OPENWEATHERMAP_HOME_CITY_ID = os.environ["OPENWEATHERMAP_CITY_ID"]
assert _OPENWEATHERMAP_HOME_CITY_ID, "No OPENWEATHERMAP_CITY_ID is set"
# slack verify token
_SLACK_TOKEN_VERIFY = os.environ["SLACK_TOKEN_VERIFY"]
assert _SLACK_TOKEN_VERIFY, "No SLACK_TOKEN_VERIFY is set"
# currency URL
_CURRENCY_URL = os.environ.get("CURRENCY_URL", "")
# currency XPath
_CURRENCY_XPATH = os.environ.get("CURRENCY_XPATH", "")

# context cache key prefix
_CONTEXT_CACHE_KEY_PREFIX = "context_"
# context cache timeout, seconds
_CONTEXT_CACHE_TIMEOUT = 10 * 24 * 60 * 60


# intent suffix
_INTENT_SUFFIX = "_intent"
# current weather intent 
_INTENT_WEATHER_CURRENT = "weather_cur_intent"
# tomorrow weather intent 
_INTENT_WEATHER_TOMORROW = "weather_tmw_intent"
# currency rate intent 
_INTENT_CURRENCY_RATE = "currency_rate_intent"
# current weather description context key
_CONTEXT_WEATHER_CURRENT_DESC = "weather_cur_desc"
# current weather temperature context key
_CONTEXT_WEATHER_CURRENT_TEMP = "weather_cur_temp"
# tomorrow weather description context key
_CONTEXT_WEATHER_TOMORROW_DESC = "weather_tmw_desc"
# tomorrow weather temperature context key
_CONTEXT_WEATHER_TOMORROW_TEMP = "weather_tmw_temp"
# currency rate context key
_CONTEXT_CURRENCY_RATE = "currency_rate"

# intent map
_INTENT_MAP = {
    _INTENT_WEATHER_CURRENT: [_CONTEXT_WEATHER_CURRENT_DESC, _CONTEXT_WEATHER_CURRENT_TEMP],
    _INTENT_WEATHER_TOMORROW: [_CONTEXT_WEATHER_TOMORROW_DESC, _CONTEXT_WEATHER_TOMORROW_TEMP],
    _INTENT_CURRENCY_RATE: [_CONTEXT_CURRENCY_RATE],
}

# calculates session ID 
def _calcSessionId(data):
    return "slack_{team}_{channel}_{user}".format(team = data["team_id"], channel = data["channel_id"], user = data["user_id"])


def _merge(session_id, context, entities, msg):
    print("_merge: entities:")
    print(entities)
    
    new_context = dict(context)
    
    # intents
    foundIntent = None
    for entity in entities.keys():
        if entity.endswith(_INTENT_SUFFIX): # intent
            foundIntent = entity
            break
            
    if foundIntent:
        for key in new_context.keys():
            if key.endswith(_INTENT_SUFFIX): # intent
                new_context.pop(key, None)

        for _, deps in _INTENT_MAP.iteritems():
            if deps:
                for dep in deps:
                    new_context.pop(dep, None)
                
        new_context[foundIntent] = " "

    print("_merge: output context:")
    print(new_context)
    
    return new_context


# fecthes current weather in home city
def _fetchWeatherCurrentHome(sessionId, context):
    out = dict(context)

    ok = False
    try:
        while True:
            repData = openweathermaputils.getCurrent(token = _OPENWEATHERMAP_TOKEN, cityId = _OPENWEATHERMAP_HOME_CITY_ID, lang = _OPENWEATHERMAP_LANG, units = _OPENWEATHERMAP_UNITS)
            if not repData:
                break
        
            (desc, temp) = openweathermaputils.getCurrentSummary(repData)
            
            out[_CONTEXT_WEATHER_CURRENT_DESC] = desc
            out[_CONTEXT_WEATHER_CURRENT_TEMP] = temp
            ok = True
            break
    except:
        print("_fetchWeatherCurrentHome: failed")
        traceback.print_exc()
        ok = False
    
    if not ok:
        out.pop(_CONTEXT_WEATHER_CURRENT_DESC, None)
        out.pop(_CONTEXT_WEATHER_CURRENT_TEMP, None)
    
    return out


# fecthes tomorrow weather in home city
def _fetchWeatherTomorrowHome(sessionId, context):
    out = dict(context)

    ok = False
    try:
        while True:
            repData = openweathermaputils.getForecastTomorrow(token = _OPENWEATHERMAP_TOKEN, cityId = _OPENWEATHERMAP_HOME_CITY_ID, lang = _OPENWEATHERMAP_LANG, units = _OPENWEATHERMAP_UNITS)
            if not repData:
                break
        
            (desc, temp) = openweathermaputils.getForecastDailySummary(repData)
            
            out[_CONTEXT_WEATHER_TOMORROW_DESC] = desc
            out[_CONTEXT_WEATHER_TOMORROW_TEMP] = temp
            ok = True
            break
    except:
        print("_fetchWeatherTomorrowHome: failed")
        traceback.print_exc()
        ok = False
    
    if not ok:
        out.pop(_CONTEXT_WEATHER_TOMORROW_DESC, None)
        out.pop(_CONTEXT_WEATHER_TOMORROW_TEMP, None)
    
    return out


# fecthes currency rate
def _fetchCurrencyRate(sessionId, context):
    out = dict(context)

    ok = False
    try:
        while True:
            if not _CURRENCY_URL or not _CURRENCY_XPATH:
                print("_fetchCurrencyRate: no url or xpath")
                break
        
            resp = requests.get(_CURRENCY_URL)
            xml = respx = ET.fromstring(resp.content)
            item = xml.find(_CURRENCY_XPATH)
            
            rate = item.text
        
            out[_CONTEXT_CURRENCY_RATE] = rate
            ok = True
            break
    except:
        print("_fetchCurrencyRate: failed")
        traceback.print_exc()
        ok = False
    
    if not ok:
        out.pop(_CONTEXT_CURRENCY_RATE, None)
    
    return out


def _processText(text, data):
    match = regex.search(r"^\s*\w+\s*[.,:!\s]\s*(?P<utterance>\S.*)\s*$", text)
    if not match:
        print("birch._processText: strange text")
        return None
        
    utterance = match.group("utterance")
    
    sessionId = _calcSessionId(data)
    
    ctxCacheKey  = cacheutils.calcCacheKey(_CONTEXT_CACHE_KEY_PREFIX, "", {"id": sessionId})
    
    ctx = cacheutils.cache.get(ctxCacheKey)

    funcs = {
        "merge": _merge,
        "fetch-weather-cur-home": _fetchWeatherCurrentHome,
        "fetch-weather-tmw-home": _fetchWeatherTomorrowHome,
        "fetch-currency-rate": _fetchCurrencyRate,
    }
    
    (answers, outerCtx) = aiwitutils.processText(_WIT_TOKEN, utterance, sessionId, funcs=funcs, context=ctx)
    print(u"q[{q}]\na[{a}]".format(q = utterance, a = "\n".join(answers)))
    
    if outerCtx:
        cacheutils.cache.set(ctxCacheKey, outerCtx, _CONTEXT_CACHE_TIMEOUT)
    
    if not answers:
        return None
    
    return "\n".join(answers)


# Implements Slack bot hook
class SlackHook(APIView):
    parser_classes = (FormParser, JSONParser,)
    permission_classes = (permissions.AllowAny,)
    renderer_classes = (JSONRenderer, )


    def post(self, request, format=None):
        print("SlackHook.post: params:{}\nbody:{}".format(request.query_params, request.data))
        
        # verify slack 
        if request.data.get("token", "") != _SLACK_TOKEN_VERIFY:
            print(u"SlackHook.post: invalid slack token:[{}]".format(request.data.get("token", "")))
            return HttpResponse(status = 404)
            
        text = request.data["text"]
        print("SlackHook.post: got text:[{text}] of type {tp}".format(text = text, tp = type(text)))
        
        try:
            answer = _processText(text, request.data)
        except:
            print("SlackHook.post: _processText failed on [{text}]".format(text = text))
            traceback.print_exc()
            answer = None
        
        if not answer:
            return HttpResponse()
            
        return Response({"text": answer})
