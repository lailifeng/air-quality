import os, glob, shutil, sys, requests, json, gzip
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
from geopy.distance import geodesic

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

class OpenAQParameterValue:
    def __init__(self, date,average):
        self.date = date
        self.average = average

class OpenAQLocation:
    def __init__(self, id, latitude,longitude):
        self.id = id
        self.latitude = latitude
        self.longitude = longitude
        self.valid_parameters = ["pm10","pm25","o3","co","no2","so2"]
        self.valid_parameter_unit = "µg/m³"
        self.pm10 = {}
        self.pm25 = {}
        self.o3 = {}
        self.co = {}
        self.no2 = {}
        self.so2 = {}
    
    def intrest_parameter(self,parameter,unit):
        if unit != self.valid_parameter_unit: 
            return False
        if parameter not in self.valid_parameters: 
            return False
        return True
    
    def add_parameter_value_into(self,d,date,value):
        year = date[:4]
        if year in d:
            d[year].append(OpenAQParameterValue(date,value))
        else:
            d[year] = [OpenAQParameterValue(date,value)]

    def add_parameter_value(self,parameter,unit,date,value):
        if not self.intrest_parameter(parameter,unit): 
            print(f"we do not intrest parameter {parameter} and unit {unit}, skip this parameter")
            return
        if parameter == "pm10":
            self.add_parameter_value_into(self.pm10,date,value)
        elif parameter == "pm25":
            self.add_parameter_value_into(self.pm25,date,value)
        elif parameter == "o3":
            self.add_parameter_value_into(self.o3,date,value)
        elif parameter == "co":
            self.add_parameter_value_into(self.co,date,value)
        elif parameter == "no2":
            self.add_parameter_value_into(self.no2,date,value)
        elif parameter == "so2":
            self.add_parameter_value_into(self.so2,date,value)
    
    def get_data_from(self,d,date):
        if date in d:
            return d[date]
        else:
            return None
    
    def get_data(self,parameter,unit,year):
        if not self.intrest_parameter(parameter,unit): 
            print(f"we do not intrest parameter {parameter} and unit {unit}, skip this parameter")
            return None
        if parameter == "pm10":
            return self.get_data_from(self.pm10,year)
        elif parameter == "pm25":
            return self.get_data_from(self.pm25,year)
        elif parameter == "o3":
            return self.get_data_from(self.o3,year)
        elif parameter == "co":
            return self.get_data_from(self.co,year)
        elif parameter == "no2":
            return self.get_data_from(self.no2,year)
        elif parameter == "so2":
            return self.get_data_from(self.so2,year)
        return None

class OpenAQLocationDistance:
    def __init__(self, id, distance):
        self.id = id
        self.distance = distance

class AirQualityData:
    def __init__(self):
        self.noaa_bucket = 'noaa-gsod-pds'
        self.noaa_cols = ['STATION','DATE','LATITUDE','LONGITUDE','TEMP','WDSP','PRCP']
        self.openaq_bucket = 'openaq-data-archive'
        self.openaq_apikey = "2d44e1026dc19e338a2a67b55febe7eece9250bcf76e7201ab5ad6f01e042cff"
        self.data_ignore_colums = ['LATITUDE','LONGITUDE','day']
        self.openaq_radius = 10000
        self.locations = {}
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

    def ungzip_openaq(self,local_directory):
        gz_files = glob.glob(os.path.join(local_directory, "*.gz"))
        if not gz_files:
            print(f"no gz file found in {local_directory}")
            return
        for gz_file in gz_files:
            output_dir = os.path.dirname(gz_file)
            base_name = os.path.basename(gz_file)
            output_file = os.path.join(output_dir, os.path.splitext(base_name)[0])
            try:
                with gzip.open(gz_file, 'rb') as f_in:
                    with open(output_file, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                print(f"ungzip: {gz_file} -> {output_file}")
            except Exception as e:
                print(f"ungzip  {gz_file} error: {e}")

    def load_openaq(self,local_directory):
        csv_files = glob.glob(os.path.join(local_directory, "*.csv"))
        if not csv_files:
            print(f"no csv file found in {local_directory}")
            return
        finished = 0
        for csv_file in csv_files:
            base_name = os.path.basename(csv_file)
            filename, ext = os.path.splitext(base_name)
            location_id_date = filename.split("-")
            if len(location_id_date) != 3:
                print(f"invalid openaq filename: {base_name}")
                finished += 1
                continue
            location_id = location_id_date[1]
            date = location_id_date[2]

            df = pd.read_csv(csv_file)
            sum = 0
            lines = 0
            parameter_name = ""
            parameter_unit = ""
            latitude = ""
            longitude = ""
            for index, row in df.iterrows():
                if latitude == "":
                    latitude = row['lat']
                if longitude == "":
                    longitude = row['lon']
                if parameter_name == "":
                    parameter_name = row['parameter']
                if parameter_unit == "":
                    parameter_unit = row['units']
                sum += row['value']
                lines += 1
            if lines > 0:
                average = sum / lines
                if location_id in self.locations:
                    location = self.locations[location_id]
                    location.add_parameter_value(parameter_name,parameter_unit,date,average)
                else:
                    location = OpenAQLocation(location_id,latitude,longitude)
                    location.add_parameter_value(parameter_name,parameter_unit,date,average)
                    self.locations[location_id] = location
            else:
                print(f"no data in {base_name}")
            finished += 1
            print(f"loaded: {finished}/{len(csv_files)}")

    
    def get_data_filename(self,parameter,start_year,end_year):
        return f"data/{parameter}_{start_year}_{end_year}.csv"
    def get_openaq_filename(self,parameter,openaq_location_id,year):
        return f"data/open-aq/{parameter}_{openaq_location_id}_{year}.csv"
    
    def nearest_openaq_location(self,latitude,longitude):
        loc = []
        x = (latitude,longitude)
        for l in self.locations.values():
            y = (l.latitude,l.longitude)
            distance = geodesic(x, y).meters
            if distance <= self.openaq_radius:
                loc.append(OpenAQLocationDistance(l.id,distance))
        loc = sorted(loc, key=lambda p: p.distance)
        return loc
    
    def match_openaq(self,latitude,longitude,openaq_parameter,year):
        # OpenAQ ASDI API Endpoint URL Base (ie: add /locations OR /averages)
        aq_df = pd.DataFrame()
        openaq_location_ids = self.nearest_openaq_location(latitude,longitude)
        if len(openaq_location_ids) > 0:
            for openaq_location_id in openaq_location_ids:
                filename = self.get_openaq_filename(openaq_parameter.name,openaq_location_id,year)
                if os.path.exists(filename):
                    # Use local data file already accessed + prepared...,
                    print('loading openaq data from local file: ', filename)
                    aq_df = pd.concat([aq_df,pd.read_csv(filename)], ignore_index=True)
                else:
                    
                    df = pd.DataFrame(columns=["day",openaq_parameter.name])
                    location = self.locations[openaq_location_id]
                    data = location.get_data(openaq_parameter.name,openaq_parameter.unit,str(year))
                    if data is not None:
                        sorted_data = sorted(data, key=lambda p: p.date)
                        for d in sorted_data:
                            new_row = pd.DataFrame({'day': [d.date[:4] + "-" + d.date[4:6] + "-" + d.date[6:8]], openaq_parameter.name: [d.average]})
                            df = pd.concat([df, new_row], ignore_index=True)
                        df.to_csv(filename, index=False)
                        aq_df = pd.concat([aq_df, df], ignore_index=True)
        return aq_df
    def merge(self,noaa_directory,openaq_parameter,start_year,end_year):
        data_filename = self.get_data_filename(openaq_parameter.name,start_year,end_year)
        data_df = pd.DataFrame()
        for year in range(start_year, end_year + 1):
            noaa_year_directory = os.path.join(noaa_directory, str(year))
            for root, dirs, files in os.walk(noaa_year_directory):
                for file in files:
                    if file.endswith('.csv'):
                        file_path = os.path.join(root, file)
                        noaa_df = pd.read_csv(file_path,usecols=self.noaa_cols)
                        noaa_df['MONTH'] = pd.to_datetime(noaa_df['DATE']).dt.month
                        noaa_first_row = noaa_df.iloc[0]
                        if(noaa_first_row is not None and noaa_first_row['LATITUDE'] and noaa_first_row['LONGITUDE']):
                            latitude = noaa_first_row['LATITUDE']
                            longitude = noaa_first_row['LONGITUDE']
                            aq_df = self.match_openaq(latitude,longitude,openaq_parameter,year)
                            if len(noaa_df) > 0 and len(aq_df) > 0:
                                df = pd.merge(noaa_df, aq_df, how="inner", left_on="DATE", right_on="day")
                                df = df.rename(columns={'average': openaq_parameter.name}).drop(columns=self.data_ignore_colums)
                                data_df = pd.concat([data_df,df], ignore_index=True)
        data_df.to_csv(data_filename, index=False)
            
