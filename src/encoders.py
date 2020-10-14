from .cli.utils import print
from json import JSONEncoder
from src import models


class ReqModelJSONEncoder(JSONEncoder):
    def default(self, object):
        if isinstance(object, models.ResultingTableauServer):
            return ResultingTableauServerJSONEncoder.default(self, object)
        else:
            # return a dictionary containing class attributes, but it does not contain attributes of type list or dict
            return object.__dict__


class ResultingTableauServerJSONEncoder(JSONEncoder):
    def default(self, object):
        if isinstance(object, models.ResultingTableauServer):
            d=object.__dict__
            d['nodes']=object.nodes
            return d
        else:
            # call base class implementation which takes care of raising exceptions for unsupported types
            return json.JSONEncoder.default(self, object)