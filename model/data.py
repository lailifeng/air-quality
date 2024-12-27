import os, glob, shutil, sys, requests, json,time
import boto3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import ipywidgets as widgets
from botocore import UNSIGNED
from botocore.config import Config
from io import StringIO
from datetime import datetime, timezone
from types import SimpleNamespace
from IPython.display import clear_output
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

def download_object_if_not_exists(downloader,s3_client, bucket_name, object_key, local_path):
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        s3_head = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        s3_size = s3_head['ContentLength']
        s3_last_modified = s3_head['LastModified']
        if os.path.exists(local_path):
            local_size = os.path.getsize(local_path)
            local_last_modified = os.path.getmtime(local_path)
            local_last_modified_utc = datetime.fromtimestamp(local_last_modified,timezone.utc).replace(tzinfo=timezone.utc)
            if local_size == s3_size and local_last_modified_utc >= s3_last_modified:
                downloader.finished_size += 1
                print(f"file {local_path} already exists and is up-to-date. skipping download.finished: {downloader.finished_size}/{downloader.total_size}")
                return
        s3_client.download_file(bucket_name, object_key, local_path)
        downloader.finished_size += 1
        print(f"downloaded {object_key} to {local_path},finished: {downloader.finished_size}/{downloader.total_size}")

    except (NoCredentialsError, PartialCredentialsError) as e:
        print(f"Error: AWS credentials not found or incomplete for {object_key}.")
    except Exception as e:
        print(f"An error occurred while downloading {object_key}: {e}")


class S3Downloader:
    def __init__(self, bucket, max_workers):
        self.bucket = bucket
        self.max_workers = max_workers
    def download(self,local_directory):
        s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))
        paginator = s3_client.get_paginator('list_objects_v2')

        if not os.path.exists(local_directory):
            os.makedirs(local_directory)
        object_keys = []
        try:
            for page in paginator.paginate(Bucket=self.bucket):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        key = obj['Key']
                        object_keys.append(key)
                        print(f"object key size: {len(object_keys)}")
        except (NoCredentialsError, PartialCredentialsError) as e:
            print("Error: AWS credentials not found or incomplete.")
        except Exception as e:
            print(f"An error occurred: {e}")

        self.total_size = len(object_keys)
        self.finished_size = 0
        print(f"file size: {self.total_size}")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for object_key in object_keys:
                local_path = os.path.join(local_directory, object_key)
                futures.append(executor.submit(download_object_if_not_exists, self,s3_client, self.bucket, object_key, local_path))
            for future in as_completed(futures):
                future.result()

class OpenAQParameter:
    def __init__(self, id, name,unit):
        self.id = id
        self.name = name
        self.unit = unit

class AirQualityData:
    def __init__(self):
        self.noaa_bucket = 'noaa-gsod-pds'
        self.noaa_cols = ['STATION','DATE','LATITUDE','LONGITUDE','TEMP','WDSP','PRCP']
        self.openaq_bucket = 'openaq-data-archive'
        self.openaq_apikey = "2d44e1026dc19e338a2a67b55febe7eece9250bcf76e7201ab5ad6f01e042cff"
        self.openaq_columns = ['day','parameter','unit','average'] 
        self.data_ignore_colums = ['DATE','LATITUDE','LONGITUDE','day','unit','parameter']
        self.openaq_radius = 10000
    def download_noaa(self,local_directory):
        # ASDI Dataset Name: NOAA GSOD,
        # ASDI Dataset URL : https://registry.opendata.aws/noaa-gsod/
        # NOAA GSOD README : https://www.ncei.noaa.gov/data/global-summary-of-the-day/doc/readme.txt
        # NOAA GSOD data in S3 is organized by year and Station ID values, so this is straight-forward
        # Example S3 path format => s3://noaa-gsod-pds/{yyyy}/{stationid}.csv
        downloader = S3Downloader(self.noaa_bucket,100)
        downloader.download(local_directory)
    def download_openaq(self,local_directory):
        # ASDI Dataset Name: OpenAQ
        # ASDI Dataset URL : https://registry.opendata.aws/openaq/
        # OpenAQ README : https://docs.openaq.org/
        downloader = S3Downloader(self.openaq_bucket,100)
        downloader.download(local_directory)
    
    def get_data_filename(self,parameter,start_year,end_year):
        return f"data/{parameter}_{start_year}_{end_year}.csv"
    def get_openaq_filename(self,parameter,openaq_location_id,year):
        return f"data/open-aq/{parameter}_{openaq_location_id}_{year}.csv"
    def get_openaq_station_filename(self,station_id):
        return f"data/open-aq/{station_id}.txt"
    
    def request_with_wait(self,url,params,headers):
        while True:
            resp = requests.get(url=url,params=params, headers=headers)
            if resp.status_code == 429:
                print("OPENAQ RATE LIMITED,Wait 100 ms")
                time.sleep(0.1)
            else:
                return resp
            
    def match_openaq(self,station,latitude,longitude,openaq_parameter,year):
        # OpenAQ ASDI API Endpoint URL Base (ie: add /locations OR /averages)
        aq_df = pd.DataFrame()
        openaq_location_ids = []
        base_url = "https://api.openaq.org/v2" 
        station_filename = self.get_openaq_station_filename(station)
        if os.path.exists(station_filename):
            # Use local data file already accessed + prepared...,
            print('loading openaq ids from local file: ', station_filename)
            with open(station_filename, 'r') as file:
                openaq_location_ids_json = file.read()
            openaq_location_ids = json.loads(openaq_location_ids_json)
        else:
            params = {
                    'coordinates': f'{latitude},{longitude}',
                    'radius': self.openaq_radius,
                    'limit': 100
            }
            headers = {
                "X-API-Key": self.openaq_apikey
            }
            resp = self.request_with_wait(url=base_url + "/locations",params=params, headers=headers)
            if resp.status_code != 200: 
                print(f"NO OpenAQ Location IDs found of NOAA Station {station} by status code: {resp.status_code}.")
                return aq_df
            
            data = resp.json()
            if data['results'] and len(data['results']) > 0:
                for i in range(0, len(data['results'])):
                    openaq_location_ids.append(data['results'][i]['id'])
                print(f"OpenAQ Location IDs of NOAA Station {station} at {latitude},{longitude}: {openaq_location_ids}")
            else:
                print(f"NO OpenAQ Location IDs found of NOAA Station {station}. CANNOT PROCEED.")

            openaq_location_ids_json = json.dumps(openaq_location_ids)
            with open(station_filename, 'w') as file:
                file.write(openaq_location_ids_json)
        
        if len(openaq_location_ids) > 0:
            for openaq_location_id in openaq_location_ids:
                filename = self.get_openaq_filename(openaq_parameter.name,openaq_location_id,year)
                if os.path.exists(filename):
                    # Use local data file already accessed + prepared...,
                    print('loading openaq data from local file: ', filename)
                    aq_df = pd.concat([aq_df,pd.read_csv(filename)], ignore_index=True)
                else:
                    # Access + prepare data (NOTE: calling OpenAQ API one year at a time to avoid timeouts),
                    print('Accessing ASDI-hosted OpenAQ Averages (HTTPS API)...')
                    params = {
                        'date_from': f'{year}-01-01',
                        'date_to': f'{year}-12-31',
                        'parameters_id': openaq_parameter.id,
                        'locations_id': openaq_location_id,
                        'limit': 366,
                        'temporal': 'day',
                        'spatial': 'location',
                    }
                    headers = {
                        "X-API-Key": self.openaq_apikey
                    }
                    resp = self.request_with_wait(url=base_url + "/averages", params=params,headers=headers)
                    if resp.status_code != 200: 
                        print(f"query openaq average of NOAA station {station} error by status code: {resp.status_code}.")
                        continue
                    data = resp.json()
                    if data['results'] and len(data['results']) > 0:
                        print(f"openaq average of NOAA station {station} data size: {len(data['results'])} ,parameter: {openaq_parameter.name}, location: {openaq_location_id}, year: {year}.")
                        df = pd.json_normalize(data['results'])
                        df = df[self.openaq_columns]
                        df = df.dropna(subset=self.openaq_columns)
                        df.to_csv(filename, index=False)
                        aq_df = pd.concat([aq_df, df], ignore_index=True)
                    else:
                        print(f"openaq average of NOAA station {station} empty,parameter: {openaq_parameter.name}, location: {openaq_location_id}, year: {year}.")
        return aq_df
    
    def merge(self,noaa_directory,openaq_parameter,start_year,end_year):
        data_filename = self.get_data_filename(openaq_parameter.name,start_year,end_year)
        data_df = pd.DataFrame()
        for year in range(start_year, end_year + 1):
            noaa_year_directory = os.path.join(noaa_directory, str(year))
            for root, dirs, files in os.walk(noaa_year_directory):
                finished_size = 0
                for file in files:
                    if file.endswith('.csv'):
                        file_path = os.path.join(root, file)
                        noaa_df = pd.read_csv(file_path,usecols=self.noaa_cols,dtype={'STATION': str})
                        noaa_df['MONTH'] = pd.to_datetime(noaa_df['DATE']).dt.month
                        noaa_first_row = noaa_df.iloc[0]
                        if(noaa_first_row is not None and noaa_first_row['LATITUDE'] and noaa_first_row['LONGITUDE']):
                            latitude = noaa_first_row['LATITUDE']
                            longitude = noaa_first_row['LONGITUDE']
                            filename, ext = os.path.splitext(file)
                            aq_df = self.match_openaq(filename,latitude,longitude,openaq_parameter,year)
                            if len(noaa_df) > 0 and len(aq_df) > 0:
                                df = pd.merge(noaa_df, aq_df, how="inner", left_on="DATE", right_on="day")
                                df = df.rename(columns={'average': openaq_parameter.name}).drop(columns=self.data_ignore_colums)
                                data_df = pd.concat([data_df,df], ignore_index=True)
                                data_df.to_csv(data_filename, index=False)
                    finished_size += 1
                    print(f"merge progress: {finished_size}/{len(files)}, year: {year}")
            





