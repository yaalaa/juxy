#!/usr/bin/python
# -*- coding: utf-8 -*-
from   __future__   import unicode_literals
from django.core.cache import cache
import urllib


# calculates cache key
def calcCacheKey(prefix, api, args):
    out = prefix + "://" + urllib.quote_plus(api.encode("utf-8"))
    
    if args:
        out = out + "?" + "&".join(["=".join((urllib.quote_plus(str(key)), urllib.quote_plus(str(args[key])))) for key in sorted(args.keys())])
    
    return out

