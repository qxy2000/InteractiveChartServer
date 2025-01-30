from flask import Blueprint
from flask_restful import Api
from .generate import Generate
from .fact import Fact

api_blueprint = Blueprint("api", __name__)
api = Api(api_blueprint)

api.add_resource(Fact, '/fact')
api.add_resource(Generate, '/generate')
