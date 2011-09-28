
from subsdownloader.providers import opensubtitles

# Name : Provider Class
MAP = {'opensubtitles.org': opensubtitles.Connection}

_INSTANCES = None

def init():
    global _INSTANCES
    _INSTANCES = [v() for k, v in MAP.iteritems()]
    return _INSTANCES

def terminate():
    global _INSTANCES
    [prov.close() for prov in _INSTANCES]
