import os,json
import pandas as pd
from geopy.distance import geodesic



class Station:
    def __init__(self,id,latitude,longitude):
        self.id = id
        self.latitude = latitude
        self.longitude = longitude

    def to_dict(self):
        return {
            'id': self.id,
            'lat': self.latitude,
            'lon': self.longitude
        }


    @classmethod
    def from_dict(cls, data):
        return cls(
            id = data['id'],
            latitude = data['lat'],
            longitude = data['lon']
        )

def dict_to_json_serializable(data):
    return {key: value.to_dict() for key, value in data.items()}
def json_to_dict_with_objects(data):
    return {key: Station.from_dict(value) for key, value in data.items()}

class StationManager:
    def __init__(self,noaa_directory):
        self.start_year = 2018
        self.end_year = 2024
        self.noaa_cols = ['STATION','LATITUDE','LONGITUDE']
        self.radius = 30000
        self.station_cache_filename = "cache/stations.json"
        self.stations = self.load_stations(noaa_directory)

    def load_stations(self,noaa_directory):
        stations = {}
        if os.path.exists(self.station_cache_filename):
            with open(self.station_cache_filename, 'r') as file:
                loaded_data = json.load(file)
            stations = json_to_dict_with_objects(loaded_data)
            print(f"loaded stations from cache, size: {len(stations)}")
            return stations
        else:
            for year in range(self.start_year, self.end_year + 1):
                noaa_year_directory = os.path.join(noaa_directory, str(year))
                for root, dirs, files in os.walk(noaa_year_directory):
                    for file in files:
                        if file.endswith('.csv'):
                            filename, ext = os.path.splitext(file)
                            if filename not in stations.keys():
                                file_path = os.path.join(root, file)
                                noaa_df = pd.read_csv(file_path,usecols=self.noaa_cols,dtype={'STATION': str},nrows=1)
                                noaa_first_row = noaa_df.iloc[0]
                                if(noaa_first_row is not None and noaa_first_row['LATITUDE'] and noaa_first_row['LONGITUDE']):
                                    latitude = noaa_first_row['LATITUDE']
                                    longitude = noaa_first_row['LONGITUDE']
                                    if pd.isna(latitude) or pd.isna(longitude):
                                        continue
                                    stations[filename] = Station(filename,latitude,longitude)
            with open(self.station_cache_filename, 'w') as file:
                json.dump(dict_to_json_serializable(stations), file)
            print(f"loaded station size: {len(stations)}")
            return stations
    
    def nearest_station(self,latitude,longitude):
        min_distance = -1
        min_station = None
        x = (latitude,longitude)
        for s in self.stations.values():
            y = (s.latitude,s.longitude)
            distance = geodesic(x, y).meters
            if min_station is None or distance <= min_distance:
                min_distance = distance
                min_station = s
        print(f"nearest station: {min_station.id}, distance: {min_distance}")
        if min_distance > self.radius:
            return None
        return min_station
