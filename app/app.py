from flask import Flask, request, render_template, jsonify
import pickle
import pandas as pd
import numpy as np
import requests
import re
from collections import defaultdict
from collections import namedtuple
from utils import object_storer
import argparse
import time
import folium
from folium.plugins import MarkerCluster
from folium.plugins import FastMarkerCluster
import boto3
from boto3.dynamodb.conditions import Key, Attr
import json
import decimal
app = Flask(__name__)


def make_popup(row):
    return folium.Popup("Load ID: " + row['load_id']+ "<br>"+ row['title'] +"<br>"+row['address'] + " <br>" + \
                        row['city'] + " "+ row['state'],
                         max_width=150)

def get_bearing(p1, p2):

    '''
    Returns compass bearing from p1 to p2

    Parameters
    p1 : namedtuple with lat lon
    p2 : namedtuple with lat lon

    Return
    compass bearing of type float

    Notes
    Based on https://gist.github.com/jeromer/2005586
    '''

    long_diff = np.radians(p2.lon - p1.lon)

    lat1 = np.radians(p1.lat)
    lat2 = np.radians(p2.lat)

    x = np.sin(long_diff) * np.cos(lat2)
    y = (np.cos(lat1) * np.sin(lat2)
        - (np.sin(lat1) * np.cos(lat2)
        * np.cos(long_diff)))

    bearing = np.degrees(np.arctan2(x, y))

    # adjusting for compass bearing
    if bearing < 0:
        return bearing + 360
    return bearing


def get_arrows(locations, color='blue', size=6, n_arrows=3):

    '''
    Get a list of correctly placed and rotated
    arrows/markers to be plotted

    Parameters
    locations : list of lists of lat lons that represent the
                start and end of the line.
                eg [[41.1132, -96.1993],[41.3810, -95.8021]]
    arrow_color : whatever folium can use.  default is 'blue'
    size : default is 6
    n_arrows : number of arrows to create.  default is 3

    Return
    list of arrows/markers
    '''

    Point = namedtuple('Point', field_names=['lat', 'lon'])

    # creating point from our Point named tuple
    p1 = Point(locations[0][0], locations[0][1])
    p2 = Point(locations[1][0], locations[1][1])

    # getting the rotation needed for our marker.
    # Subtracting 90 to account for the marker's orientation
    # of due East(get_bearing returns North)
    rotation = get_bearing(p1, p2) +90

    # get an evenly space list of lats and lons for our arrows
    # note that I'm discarding the first and last for aesthetics
    # as I'm using markers to denote the start and end
    arrow_lats = np.linspace(p1.lat, p2.lat, n_arrows + 2)[1:n_arrows+1]
    arrow_lons = np.linspace(p1.lon, p2.lon, n_arrows + 2)[1:n_arrows+1]

    arrows = []

    #creating each "arrow" and appending them to our arrows list
    for points in zip(arrow_lats, arrow_lons):
        arrows.append(folium.RegularPolygonMarker(location=points,
                      fill_color=color, number_of_sides=3,
                      radius=size, rotation=rotation))
    return arrows

def get_job_df(map,mc,table,job_id):
    """This method will make a query to the job_detail table and plot it on a folium map object with
    directed arrows."""

    #query the job task table for the given job id
    fe = Key('job_id').eq(job_id)
    resp = table.scan(FilterExpression = fe)['Items']
    df = pd.DataFrame(resp).sort_values(by = 'id').reset_index()
    num_stops = len(df)
    df['stop']= df.index+1
    # get location info (will be removed in future)
    df['lat']=df.apply(lambda x: lat_dict[(x['address']+ " " + x['city']+" " +x['state']).lower()],axis = 1)
    df['lon']=df.apply(lambda x: lon_dict[(x['address']+ " " +x['city']+" " +x['state']).lower()],axis = 1)
    #shift for plotting lines
    df['lat_st']=df['lat'].shift(1)
    df['lon_st']=df['lon'].shift(1)
    return df

def plot_job_df(map,mc,df):
    """This method will take a dataframe containing all tasks for a job, and then plot it on a map object if
    it is a valid job. """

    #if all locations have coordinates, plot the job.
    if (len(df)> 0) & (len(df[df['lon']==0])==0):
        colors = defaultdict(lambda: 'blue')
        colors[1]='green'
        colors[df['stop'].max()]='red'
        for row in df.iterrows():
            mc.add_child(folium.Marker(location = [row[1]['lat'],row[1]['lon']],
                                       popup= make_popup(row[1]),
                          icon=folium.Icon(color=colors[int(row[1]['stop'])])))
        for row in df.dropna(subset = ['lat_st']).iterrows():
            p1 = [row[1]['lat'],row[1]['lon']]
            p2 = [row[1]['lat_st'],row[1]['lon_st']]
            folium.PolyLine(locations=[p1, p2], color='blue',).add_to(map)
            arrows = get_arrows(locations=[p1, p2], color='#FFFFFF', n_arrows=3)
            for arrow in arrows:
                arrow.add_to(map)


    return None

def make_map(): ## Run this inside the homepage route

    table = dynamodb.Table('job_task')
    map = folium.Map(location=[40.7128, -74.0060],zoom_start=9)
    mc = MarkerCluster()
    df = pd.DataFrame()
    all_jobs = pd.DataFrame()
    jobs = set()

    user_id='d65cb4f0-8eb7-11e9-b024-39da2a204b63'

    fe = Key('created_by').eq(user_id)
    pe = "job_id"
    resp = table.scan(ProjectionExpression = pe, FilterExpression = fe)['Items']

    for elem in resp:
        jobs.add(elem['job_id'])
    for job in jobs:
        all_jobs = all_jobs.append(get_job_df(map,mc,table,job))

    table = dynamodb.Table('job')

    fe = Key('user_id').eq(user_id)
    resp = table.scan( FilterExpression = fe)['Items']
    job_cols = ['id','load_id','title']
    all_jobs = all_jobs.merge(pd.DataFrame(resp)[job_cols],how = 'left',left_on='job_id',right_on = 'id')

    df = all_jobs[all_jobs['lat']!= 0]
    grp = all_jobs.groupby(by = 'job_id')

    grp.agg(lambda x: plot_job_df(map,mc,x))
    map.fit_bounds([[df['lat'].min(),df['lon'].min()],
                    [df['lat'].max(),df['lon'].max()]])
    map.add_child(mc)
    map.save('templates/map.html')
    return None

@app.route('/')
def submission_page_default():
    return render_template('index2.html', map_html = store.map_html)

if __name__ == '__main__':


    lat_dict = defaultdict(int)
    lon_dict = defaultdict(int)
    address = "9 Ten Broeck Pl albany NY".lower()
    lat_dict[address] = 42.658293
    lon_dict[address] = -73.751163

    address = "123 main street columbus OH".lower()
    lat_dict[address] = 39.955681
    lon_dict[address] = -83.002757

    address = "123 main st columbus OH".lower()
    lat_dict[address] = 39.955681
    lon_dict[address] = -83.002757

    address = "123 e broadway new york ny".lower()
    lat_dict[address] = 40.734749
    lon_dict[address] = -73.990611

    address = "123 main street philadelphia PA".lower()
    lat_dict[address] = 40.022975
    lon_dict[address] = -75.219292

    address = "355 grand st jersey city NJ".lower()
    lat_dict[address] = 40.715257
    lon_dict[address] = -74.050824

    address = "206 Springfield ave newark NJ".lower()
    lat_dict[address] = 40.736681
    lon_dict[address] = -74.186132

    address = "600 N charles st baltimore MD".lower()
    lat_dict[address] = 39.296570
    lon_dict[address] = -76.616106

    dynamodb = boto3.resource('dynamodb', region_name='us-east-2')

    make_map()
    store = object_storer()
    app.run(host='0.0.0.0', port=8081, debug=True)
