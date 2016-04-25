#!/usr/bin/python
# -*- coding: utf-8 -*-
from   __future__   import unicode_literals
import os

from wit import Wit


# access token
_SERVER_TOKEN = os.environ["WIT_TOKEN"]
assert _SERVER_TOKEN, "No WIT_TOKEN set"


def firstEntityValue(entities, entity):
    if entity not in entities:
        return None
    val = entities[entity][0]['value']
    if not val:
        return None
    return val['value'] if isinstance(val, dict) else val


def _mergeDefault(session_id, context, entities, msg):
    print("_merge: entities:")
    print(entities)
    
    new_context = dict(context)
    
    return new_context


def processText(text, sessionId, funcs=None, context=None):
    out = []
    
    def say(session_id, context, msg):
        out.append(msg)

    def error(session_id, context, msg):
        print(u"aiwitutils.processText.error: [{msg}]".format(msg=msg))
        pass
    
    actions = dict(funcs) if isinstance(funcs, dict) else {}
    actions["say"] = say
    actions["error"] = error
    
    if "merge" not in actions:
        actions["merge"] = _mergeDefault
    
    client = Wit(_SERVER_TOKEN, actions)
    
    inCtx = context if context else {}
    
    outerCtx = client.run_actions(sessionId, text, inCtx)

    return (out, outerCtx)

