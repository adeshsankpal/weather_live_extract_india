# -*- coding: utf-8 -*-
"""Weather_Data_Live.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/193Q9d4yOWNQirTLu_3H0mXGenVG8_U_E
"""

!pip install imdlib
!pip install mongo

import imdlib as imd
import pandas as pd
from datetime import datetime,timedelta
import pytz
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from math import radians, sin, cos, sqrt, atan2

def connect_db(url,db,collection):
  uri = url
  # Create a new client and connect to the server
  client = MongoClient(uri, server_api=ServerApi('1'))
  client.admin.command('ping')
  db=client[db]
  table_r=db[collection]
  return table_r

def now():
  # Get the current UTC time
  utc_now = datetime.utcnow()

  # Specify the source timezone (UTC)
  utc_timezone = pytz.timezone('UTC')

  # Localize the UTC time to convert it to IST
  localized_utc_now = utc_timezone.localize(utc_now)

  # Specify the target timezone (IST)
  ist_timezone = pytz.timezone('Asia/Kolkata')  # IST timezone

  # Convert the localized time to IST
  ist_now = localized_utc_now.astimezone(ist_timezone)

  return ist_now

def download_daily(start,end,var):
  start_dy = start
  end_dy = end
  var_type = var
  data = imd.get_real_data(var_type, start_dy, end_dy)
  return data

def convert_to_df(data,var):
  ds = data.get_xarray()
  dfs = {}
  for var_name, var_data in ds.items():
      dfs[var_name] = var_data.to_dataframe()

  valid_dfs = {key: df for key, df in dfs.items() if not df.empty and df.ndim > 1}
  # Create the final DataFrame by concatenating valid DataFrames
  df = pd.concat(valid_dfs.values(), axis=1)
  # Optionally, reset the index if needed
  if var=='rain':
    df = df[df['rain'] != -999.0]
  #data_dict = df.to_dict(orient='records')
  df.reset_index(inplace=True)
  return df

def full_temp_data(loc_nearby,df_tm,var):
  min_distance_indices = loc_nearby.groupby(['lat', 'lon'])['distance'].idxmin()
  # Filter the DataFrame using the indices of minimum distance
  min_distance_indices = loc_nearby.loc[min_distance_indices]
  min_distance_indices=min_distance_indices.reset_index(drop=True)
  min_distance_indices=pd.merge(min_distance_indices,df_tm,on=['lat_nearby','lon_nearby'],how='left')
  min_distance_indices['lon'] = min_distance_indices['lon'].fillna(min_distance_indices['lon_nearby'])
  min_distance_indices['lat'] = min_distance_indices['lat'].fillna(min_distance_indices['lat_nearby'])
  min_distance_indices=min_distance_indices[['time','lat','lon',var]]
  df_tm = df_tm.rename(columns={'lat_nearby': 'lat', 'lon_nearby': 'lon'})
  min_distance_indices = pd.concat([min_distance_indices, df_tm])
  min_distance_indices.reset_index(drop=True, inplace=True)
  return min_distance_indices

url3="mongodb+srv://parameter:parameter@cluster0.va2sth1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
location_table='nearby_location'
db_india='india'
location_table=connect_db(url3,db_india,location_table)
loc_nearby=pd.DataFrame(list(location_table.find()))

def spatial_data():
  url2="mongodb+srv://parameter:parameter@cluster0.va2sth1.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
  spatial='spatial'
  db_india='india'
  spatial_table=connect_db(url2,db_india,spatial)
  data_spatial=pd.DataFrame(list(spatial_table.find()))
  return data_spatial

url="mongodb+srv://weather1:weather1@cluster0.d5tkbqr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
table_name='weather_2021'
db='W_India_2021'
table=connect_db(url,db,table_name)

m_date = table.find_one(sort=[('time', -1)])
m_date=m_date['time']
m_date = m_date.replace(tzinfo=None)
m_date = m_date + timedelta(days=1)
time_now=now()
date_5_days_ago = time_now - timedelta(days=5)
date_to_delete=date_5_days_ago
time_now = time_now + timedelta(days=-1)
date_5_days_ago = date_5_days_ago + timedelta(days=1)
date_5_days_ago = date_5_days_ago.replace(tzinfo=None)
start_day=date_5_days_ago.strftime('%Y-%m-%d')
end_day=time_now.strftime('%Y-%m-%d')
if m_date<=date_5_days_ago:
  start_day=m_date.strftime('%Y-%m-%d')

data=download_daily(start_day,end_day,'rain')
data=convert_to_df(data,'rain')
data_tmax=download_daily(start_day,end_day,'tmax')
data_tmax=convert_to_df(data_tmax,'tmax')
data_tmax = data_tmax.rename(columns={'lat': 'lat_nearby', 'lon': 'lon_nearby'})
data_tmax=full_temp_data(loc_nearby,data_tmax,'tmax')
data_tmin=download_daily(start_day,end_day,'tmin')
data_tmin=convert_to_df(data_tmin,'tmin')
data_tmin = data_tmin.rename(columns={'lat': 'lat_nearby', 'lon': 'lon_nearby'})
data_tmin=full_temp_data(loc_nearby,data_tmin,'tmin')
data=pd.merge(data,data_tmax,on=['time','lon','lat'],how='left')
data=pd.merge(data,data_tmin,on=['time','lon','lat'],how='left')
data_spatial=spatial_data()
# Concatenate the columns 'state_district', 'state', and 'country' into a single column with "|" separator
data_spatial['location'] = data_spatial.apply(lambda row: f"{row['state_district']}|{row['state']}|{row['country']}", axis=1)
# Drop the original columns
data_spatial.drop(columns=['state_district', 'state', 'country'], inplace=True)
data=pd.merge(data,data_spatial,on=['lat','lon'],how='left')
data=data[['time','location','rain','tmax','tmin']]
data = data.groupby(['time', 'location']).agg({'rain': 'mean', 'tmax': 'mean', 'tmin': 'mean'}).reset_index()
data=data.to_dict(orient='records')
# Round Numeric Values
for record in data:
    record['rain'] = round(record['rain'], 1)
    record['tmax'] = round(record['tmax'], 1)
    record['tmin'] = round(record['tmin'], 1)
delete_result = table.delete_many({"time": {"$gte": date_to_delete}})
x=table.insert_many(data)