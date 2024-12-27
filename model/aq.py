import argparse
from datetime import datetime
import data as d
import train as t

class AirQualityEntity:
    def __init__(self,parameter,train_data_file,model_path):
        self.parameter = parameter
        self.train_data_file = train_data_file
        self.model_path = model_path

class AirQuality:
    def __init__(self):
        self.targets = [
            AirQualityEntity(d.OpenAQParameter(1,"pm10","µg/m³"),"data/train/pm10.csv","model-pm10"),
            AirQualityEntity(d.OpenAQParameter(2,"pm25","µg/m³"),"data/train/pm25.csv","model-pm25"),
            AirQualityEntity(d.OpenAQParameter(3,"o3","µg/m³"),"data/train/o3.csv","model-o3"),
            AirQualityEntity(d.OpenAQParameter(4,"co","µg/m³"),"data/train/co.csv","model-co"),
            AirQualityEntity(d.OpenAQParameter(5,"no2","µg/m³"),"data/train/no2.csv","model-no2"),
            AirQualityEntity(d.OpenAQParameter(6,"so2","µg/m³"),"data/train/so2.csv","model-so2")
        ]
        self.noaa_data_path = "data/noaa-gsod"
        self.openaq_data_path = "data/open-aq"
        self.preprocess_start_year = 2019
        self.preprocess_end_year = 2020

    def download_data(self):
        aqdata = d.AirQualityData()
        aqdata.download_noaa(self.noaa_data_path)
        aqdata.download_openaq(self.openaq_data_path)

    def preprocess(self):
        aqdata = d.AirQualityData()
        for t in self.targets:
            aqdata.merge(self.noaa_data_path,
                         t.parameter,
                         self.preprocess_start_year,
                         self.preprocess_end_year)

    def train(self,index):
        if index < 0 or index >= len(self.targets):
            print(f"train index out of range: [0, {len(self.targets)})")
            return
        now = datetime.now()
        current_time_str = now.strftime('%Y%m%d%H%M%S')
        aq_train = t.AirQualityTrain(
            self.targets[index].parameter.name,
            self.targets[index].train_data_file,
            self.targets[index].model_path + "/" + current_time_str)
        aq_train.train()

    def predict(self):
        aq_train = t.AirQualityPredict("model-pm25/20241224204155")
        aq_train.predict("03318099999",45.1,10.3,0.01,12)
        aq_train.predict("03318099999",43.3,15.9,0.01,12)
        aq_train.predict("03318099999",37.8,14.9,0.0,12)
        aq_train.predict("03318099999",43.8,13.6,0.2,12)
        aq_train.predict("03318099999",45.3,12.0,0.2,12)

def main(args):
    if args.action is None:
        print("need parameter --action")
        return
    print(f"action is {args.action}")
    aq = AirQuality()
    if args.action == "download":
        aq.download_data()
    if args.action == "preprocess":
        aq.preprocess()
    if args.action == "train":
        if args.p is None:
            print("need parameter --p")
            return
        aq.train(args.p)
    if args.action == "predict":
        aq.predict()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="predicting air qualityAir program.")
    parser.add_argument("--action", type=str, help="the action")
    parser.add_argument('--p', type=int, help='the parameter of action')
    
    args = parser.parse_args()
    main(args)