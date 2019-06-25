from flask import Flask, request, render_template, jsonify
from flask.globals import request

import boto3
from boto3.dynamodb.conditions import Key, Attr

import json
import pandas as pd
import numpy as np
import requests
import re
from collections import defaultdict
from collections import namedtuple
import time

from utils import object_storer

app = Flask(__name__)

def get_user_addresses():

@app.route('/')
def submission_page_default():
    return render_template('index_here.html', map_html = "<br>")


if __name__ == '__main__':
    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
    store = object_storer()
    app.run(host='0.0.0.0', port=8081, debug=True)
