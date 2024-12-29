import model as m
from datetime import date, timedelta
import requests,os,json
import station
import aqi

class AirQualityEntity:
    def __init__(self,parameter,model_path,log_increment):
        self.parameter = parameter
        self.model_path = model_path
        self.log_increment = log_increment
        self.predictor = m.AirQualityPredictor(model_path,self.log_increment)

class City:
    def __init__(self,code,qweather_id,latitude,longitude,country,station):
        self.code = code
        self.qweather_id = qweather_id
        self.latitude = latitude
        self.longitude = longitude
        self.country = country
        self.station = station

class AirQuality:
    def __init__(self,noaa_data_path):
        self.targets = [
            AirQualityEntity("pm10","model/pm10",1),
            AirQualityEntity("pm25","model/pm25",1),
            AirQualityEntity("o3","model/o3",1),
            AirQualityEntity("co","model/co",0.001),
            AirQualityEntity("no2","model/no2",1),
            AirQualityEntity("so2","model/so2",1)
        ]
        self.cities = {}
        self.qweather_api_key = "c6f024bd8b1940b3a8b663ca6739463e"
        self.stations = station.StationManager(noaa_data_path)

    def kmh_to_ms(self,kmh):
        return kmh / 3.6
    
    def get_location(self,city):
        if city in self.cities.keys():
            return self.cities[city]
        location =  self.get_location_from_qweather(city)
        if location is None:
            return None
        station = self.stations.nearest_station(location[1],location[2])
        if station is None:
            return None
        city = City(city,location[0],location[1],location[2],location[3],station)
        self.cities[city] = city
        return city
    
    def get_location_from_qweather(self,city):
        params = {
                'location': city
        }
        headers = {
            "X-QW-Api-Key": self.qweather_api_key
        }
        resp = requests.get(url="https://geoapi.qweather.com/v2/city/lookup",params=params, headers=headers)
        if resp.status_code != 200: 
            print(f"lookup location from qwather of city {city} error status code: {resp.status_code}.")
            return None
        data = resp.json()
        if data['code'] and data["code"] == '200' and data["location"] and len(data['location']) > 0:
            id = data['location'][0]['id']
            lantitude = data['location'][0]['lat']
            longitude = data['location'][0]['lon']
            country = data['location'][0]['country']
            print(f"lookup location from qwather of city {city} success, id: {id}, lantitude: {lantitude}, longitude: {longitude}, country: {country}.")
            return (id,lantitude,longitude,country)
        else:
            print(f"lookup location from qwather of city {city} error.")
        return None
            
    def get_tommorrow_weather_from_qweather(self,city,qweather_city_id):
        params = {
                'location': qweather_city_id
        }
        headers = {
            "X-QW-Api-Key": self.qweather_api_key
        }
        resp = requests.get(url="https://api.qweather.com/v7/weather/3d",params=params, headers=headers)
        if resp.status_code != 200: 
            print(f"query weather from qwather of city {city} error status code: {resp.status_code}.")
            return None
        data = resp.json()
        if data['code'] and data["code"] == '200' and data["daily"] and len(data['daily']) > 0:
            today = date.today()
            tomorrow = today + timedelta(days=1)
            tomorrow_str = tomorrow.strftime('%Y-%m-%d')
            for i in range(len(data['daily'])):
                if data['daily'][i]['fxDate'] == tomorrow_str:
                    temp = (float(data['daily'][i]['tempMax']) + float(data['daily'][i]['tempMin'])) / 2
                    wdsp = self.kmh_to_ms(float(data['daily'][i]['windSpeedDay']))
                    prcp = float(data['daily'][i]['precip'])
                    return (temp,wdsp,prcp)
        else:
            print(f"query weather from qwather of city {city} error.")
        return None
    
    def predict_tommorrow_air_quality(self,station,temp,wdsp,prcp):
        today = date.today()
        tomorrow = today + timedelta(days=1)
        month = tomorrow.month
        predicts = {}
        for target in self.targets:
            predicts[target.parameter] = target.predictor.predict(station.id,temp,wdsp,prcp,month)
        return predicts
    
    def aqi(self,city_info,predicts):
        if city_info.country == "中国":
            return aqi.calculate_cn_aqi(predicts)
        return aqi.calculate_us_aqi(predicts)
    
    def predict(self,city):
        today = date.today()
        tomorrow = today + timedelta(days=1)
        cache_filename = f"cache/predict-{city}-{tomorrow.strftime('%Y%m%d')}.json"
        if os.path.exists(cache_filename):
            # Use local data file already accessed + prepared...,
            print('loading predict from local file: ', cache_filename)
            with open(cache_filename, 'r') as file:
                predicts_json = file.read()
            return json.loads(predicts_json)
        else:
            city_info = self.get_location(city)
            if city_info is None:
                return None
            weather = self.get_tommorrow_weather_from_qweather(city,city_info.qweather_id)
            if weather is None:
                return None
            predicts = self.predict_tommorrow_air_quality(city_info.station,weather[0],weather[1],weather[2])
            aqi = self.aqi(city_info,predicts)
            for k in predicts.keys():
                predicts[k] = str(round(predicts[k],2))
            predicts["aqi"] = str(round(aqi,2))
            predicts["temp"] = str(round(weather[0],2))
            predicts["wdsp"] = str(round(weather[1],2))
            predicts["prcp"] = str(round(weather[2],2))
            predicts_json = json.dumps(predicts)
            with open(cache_filename, 'w') as file:
                file.write(predicts_json)
            return predicts