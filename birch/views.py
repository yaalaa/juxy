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

import juxy.cacheutils as cacheutils
import aiwitutils


_SLACK_TOKEN_VERIFY = os.environ["SLACK_TOKEN_VERIFY"]
assert _SLACK_TOKEN_VERIFY, "No SLACK_TOKEN_VERIFY is set"

# context cache key prefix
_CONTEXT_CACHE_KEY_PREFIX = "context_"
# context cache timeout, seconds
_CONTEXT_CACHE_TIMEOUT = 10 * 24 * 60 * 60


# calculates session ID 
def _calcSessionId(data):
    return "slack_{team}_{channel}_{user}".format(team = data["team_id"], channel = data["channel_id"], user = data["user_id"])


def _merge(session_id, context, entities, msg):
    print("_merge: entities:")
    print(entities)
    
    new_context = dict(context)
    
    return new_context


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
    }
    
    (answers, outerCtx) = aiwitutils.processText(utterance, sessionId, funcs=funcs, context=ctx)
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
