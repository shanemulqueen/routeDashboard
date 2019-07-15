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
    return folium.Popup("Registered: " + row['created'],
                         max_width=150)


def is_real(elem):
    try:
        if elem['email'].split('@')[1]=='fleetingpro.com':
            return False
        elif len(elem['address'])< 4:
            return False
        elif elem['full_name'] in store.bad_names:
            return False
        elif elem['address'] in store.bad_addresses:
            return False
        elif ("{} {}".format(elem['first_name'],elem['last_name']) in store.bad_names):
            return False
        else:
            return True
    except:
        return False
def is_good_email(elem):
    try:
        if elem['email'].split('@')[1]=='fleetingpro.com':
            return False
        elif elem['email'].split('@')[1]=='upright.nyc':
            return False
        elif ("{} {}".format(elem['first_name'],elem['last_name']) in store.bad_names):
            return False
        else:
            return True
    except:
        return False


def get_user_df(map,mc,table,job_id):
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

def plot_user_df(map,mc,row):
    """This series containing containing users . """

    #if all locations have coordinates, plot the job.
    colors = defaultdict(lambda: 'blue')
    colors[1]='green'
    mc.add_child(folium.Marker(location = [row['lat'],row['lon']],
                               popup= make_popup(row),
                  icon=folium.Icon(color=colors[1])))
    return None



def make_map(): ## Run this inside the homepage route
    error_count = 0
    table = dynamodb.Table('user')
    map = folium.Map(location=[40.7128, -74.0060],zoom_start=9)
    mc = MarkerCluster()
    df = pd.DataFrame()
    user_dict = {}
    user_dict['name']= []
    user_dict['address']= []
    user_dict['modified']=[]
    user_dict['created']=[]
    user_dict['good_address']=[]
    user_dict['email']= []
    user_dict['lat']=[]
    user_dict['lon']=[]
    user_dict['Type']=[]


    email_only = {}
    email_only['name'] = []
    email_only['modified'] = []
    email_only['created'] = []
    email_only['email'] = []
    email_only['Type']=[]
    jobs = set()

    app_id = 'VeNrYq6tzUFgucRaVSsX'
    app_code = 'fCfJz6aA-zNHLgU-JOWrng'

    resp = table.scan()

    for elem in resp['Items']:
        try:
            if (is_real(elem)):
                print("{} {}".format(elem['first_name'],elem['last_name']))
                try:
                    user_dict['address'].append("{} {} {}".format(elem['address'],elem['city'],elem['state']))
                except:
                    user_dict['address'].append("{} {} {}".format(elem['address'],'Brooklyn','NY'))
                user_dict['email'].append(elem['email'])
                user_dict['name'].append("{} {}".format(elem['first_name'],elem['last_name']))
                user_dict['Type'].append(store.user_type[elem['type']])
                epoch = int(str(elem['created_dt'])[:-3])
                user_dict['created'].append(time.strftime("%Y-%m-%d", time.localtime(epoch)))
                epoch = int(str(elem['modified_dt'])[:-3])
                user_dict['modified'].append(time.strftime("%Y-%m-%d", time.localtime(epoch)))
                print("success")
            else:
                try:
                    asdf = elem['address']
                except:
                    try:
                        if is_good_email(elem):
                            email_only['name'].append("{} {}".format(elem['first_name'],elem['last_name']))
                            epoch = int(str(elem['created_dt'])[:-3])
                            email_only['created'].append(time.strftime("%Y-%m-%d", time.localtime(epoch)))
                            epoch = int(str(elem['modified_dt'])[:-3])
                            email_only['modified'].append(time.strftime("%Y-%m-%d", time.localtime(epoch)))
                            email_only['email'].append(elem['email'])
                            email_only['Type'].append(store.user_type[elem['type']])
                    except:
                        print(elem['email'])
        except:
            error_count +=1
            print('bad')
            try:
                asdf = elem['address']
            except:
                try:
                    if is_good_email(elem):
                        email_only['name'].append("{} {}".format(elem['first_name'],elem['last_name']))
                        epoch = int(str(elem['created_dt'])[:-3])
                        email_only['created'].append(time.strftime("%Y-%m-%d", time.localtime(epoch)))
                        epoch = int(str(elem['modified_dt'])[:-3])
                        email_only['modified'].append(time.strftime("%Y-%m-%d", time.localtime(epoch)))
                        email_only['email'].append(elem['email'])
                        email_only['Type'].append(store.user_type[elem['type']])
                except:
                    print(elem['email'])

    for address in user_dict['address']:
        #try:
        uri = 'https://geocoder.cit.api.here.com/6.2/geocode.json'
        headers = {}
        params = {
                'app_id': app_id,
                'app_code': app_code,
                'searchtext': address
                }

        response = session.get(uri, headers=headers, params=params)
        response.json()['Response']['View'][0]['Result'][0]
        user_dict['good_address'].append(response.json()['Response']['View'][0]['Result'][0]['Relevance'])
        user_dict['lat'].append(response.json()['Response']['View'][0]['Result']
                                     [0]['Location']['NavigationPosition'][0]['Latitude'])
        user_dict['lon'].append(response.json()['Response']['View'][0]['Result']
                                      [0]['Location']['NavigationPosition'][0]['Longitude'])
        # except:
        #     print(address)
        #     user_dict['good_address'].append(0)
        #     user_dict['lat'].append(40.7128)
        #     user_dict['lon'].append(-74.0060)

    registered = pd.DataFrame(user_dict)
    emails = pd.DataFrame(email_only)
    print('registered length: {}'.format(len(registered)))
    print('email length: {}'.format(len(emails)))
    registered.apply(lambda x: plot_user_df(map,mc,x),axis = 1)
    map.fit_bounds([[registered['lat'].min(),registered['lon'].min()],
                    [registered['lat'].max(),registered['lon'].max()]])
    map.add_child(mc)
    map.save('templates/map_user.html')
    return registered, emails

@app.route('/')
def submission_page_default():
    [registered, emails] = make_map()
    registered['Background']='Yes'
    emails['Background']='No'
    emails['good_address']=0
    both = emails.append(registered[['name','email','modified','created','Type','Background','good_address']])
    user_html = both.sort_values(by = 'created',ascending=False).to_html(classes=['display','nowrap'],
        columns = ['name','email','modified','created','Type','Background','good_address'],
        table_id='users',index = False,justify = 'center',float_format=lambda x:'{:.1f}'.format(x))
    return render_template('index_users.html', user_html = user_html)

if __name__ == '__main__':
    session = requests.Session()
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    store = object_storer()
    app.run(host='0.0.0.0', port=8081, debug=True)
