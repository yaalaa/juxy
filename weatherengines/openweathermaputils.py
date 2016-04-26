#!/usr/bin/python
# -*- coding: utf-8 -*-
from   __future__   import unicode_literals
import requests
import os

from cacheutils import cacheutils


# cache key prefix
_CACHE_KEY_PREFIX = "openweathermap_"
# cache timeout, seconds
_CACHE_TIMEOUT = 10 * 60
# units, aka Farenheit
_UNITS = "imperial"
# language
_LANG = "en"


# calculates cache key
def _cacheKey(api, args):
    return cacheutils.calcCacheKey(_CACHE_KEY_PREFIX, api, args)


# looks for current weather report
def getCurrent(token, locationName = None, cityId = None, units = None, lang = None):
    if not locationName and not cityId:
        print("openweathermaputils.getCurrent: neither location nor city id")
        return None
        
    if not units:
        units = _UNITS
        
    if not lang:
        lang = _LANG

    cacheArgs = {
        "l": locationName if locationName else "",
        "c": cityId if cityId else "",
        "u": units,
        "lang": lang,
    }
    cacheKey = _cacheKey("current", cacheArgs)
    
    out = cacheutils.cache.get(cacheKey)

    if not out: # not in cache
        params = {
            "APPID": token,
            "q": locationName if locationName else "",
            "id": cityId if cityId else "",
            "units": units,
            "lang": lang,
        }
    
        response = requests.get("http://api.openweathermap.org/data/2.5/weather", params = params)
        
        try:
            gotJson = response.json()
        except ValueError:
            print("openweathermaputils.getCurrent: got not json[{payload}]".format(payload = response.text))
            gotJson = None
        
        if response.status_code != requests.codes.ok:
            print("openweathermaputils.getCurrent: failed with {code} json[{payload}]".format(code = response.status_code, payload = gotJson))
        else:
            out = gotJson
        
        # update cache
        cacheutils.cache.set(cacheKey, out, _CACHE_TIMEOUT)

    outFirst = None
    
    if out:
        if isinstance(out, dict):
            outFirst = out
        elif isinstance(out, list):
            outFirst = out[0]

    return outFirst


def getCurrentSummary(state):
    # clear with a temperature of 54.6° F and humidity 52%
    out = None
    
    if state and isinstance(state, dict):
        weatherBlock = state["weather"][0]
        mainBlock = state["main"]
        out = (weatherBlock["description"], mainBlock["temp"])
    
    return out


# looks for tomorrow weather report
def getForecastTomorrow(token, locationName = None, cityId = None, units = None, lang = None):
    if not locationName and not cityId:
        print("openweathermaputils.getForecast16: neither location nor city id")
        return None
        
    if not units:
        units = _UNITS
        
    if not lang:
        lang = _LANG

    cacheArgs = {
        "l": locationName if locationName else "",
        "c": cityId if cityId else "",
        "u": units,
        "lang": lang,
    }
    cacheKey = _cacheKey("tomorrow", cacheArgs)
    
    out = cacheutils.cache.get(cacheKey)

    if not out: # not in cache
        params = {
            "APPID": token,
            "q": locationName if locationName else "",
            "id": cityId if cityId else "",
            "units": units,
            "lang": lang,
            "cnt": 1,
        }
    
        response = requests.get("http://api.openweathermap.org/data/2.5/forecast/daily", params = params)
        
        try:
            gotJson = response.json()
        except ValueError:
            print("openweathermaputils.getForecastTomorrow: got not json[{payload}]".format(payload = response.text))
            gotJson = None
        
        if response.status_code != requests.codes.ok:
            print("openweathermaputils.getForecastTomorrow: failed with {code} json[{payload}]".format(code = response.status_code, payload = gotJson))
        else:
            out = gotJson
        
        # update cache
        cacheutils.cache.set(cacheKey, out, _CACHE_TIMEOUT)

    outFirst = None
    
    if out:
        outFirst = out["list"][0]

    return outFirst


def getForecastDailySummary(state):
    out = None
    
    if state and isinstance(state, dict):
        weatherBlock = state["weather"][0]
        tempBlock = state["temp"]
        out = (weatherBlock["description"], tempBlock["day"])
    
    return out


