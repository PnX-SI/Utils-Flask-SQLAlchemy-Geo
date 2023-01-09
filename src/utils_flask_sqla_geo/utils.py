from flask import jsonify


def geojsonify(*args, **kwargs):
    response = jsonify(*args, **kwargs)
    response.mimetype = "application/geo+json"
    return response
