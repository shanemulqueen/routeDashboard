import pandas as pd
import numpy as np
from splinter import Browser
from lxml import html
import requests
import bs4
import time
import urllib
import html5lib
from collections import defaultdict
from contextlib import closing

class object_storer(object):
    def __init__(self):
        f = open('templates/map0.html')

        self.map_html = ''
        for line in f:
            self.map_html += line.strip()
        self.bad_names = {'Shane Mulqueen', 'Ryan M','Ryan McCaulsky', 'Aaditya Raj Mehta', 'Male Gibson'}
        self.bad_addresses = {'222 E 39th St Apt 22B','81 Prospect Street'}
        self.map_html = "Test"

        self.user_type = defaultdict(lambda: 'driver')
        self.user_type[3]='Carrier'
        self.user_type[2]='Driver'
