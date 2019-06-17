import pandas as pd
import numpy as np
from splinter import Browser
from lxml import html
import requests
import bs4
import time
import urllib
import html5lib
from contextlib import closing

class object_storer(object):
    def __init__(self):
        f = open('templates/map0.html')

        self.map_html = ''
        for line in f:
            self.map_html += line.strip()

        self.map_html = "Test"
