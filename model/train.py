import pandas as pd
from sklearn.model_selection import train_test_split
from autogluon.tabular import TabularPredictor
import numpy as np
import os,glob,json
from datetime import datetime


class AirQualityTrain:
    def __init__(self,label,data_path,model_path,log_increment,evaluate_path):
        self.label = label
        self.data_path = data_path
        self.model_path = model_path
        self.log_increment = log_increment
        self.evaluate_path = evaluate_path
        now = datetime.now()
        self.timestemp = now.strftime('%Y%m%d%H%M%S')
    
    def before_train(self,df):
        df = df[df[self.label] >= 0] # skip nagative value
        if(self.label == "co"):
            print(f"update co label,change μg/m³ to mg/m³")
            df.loc[:, self.label] = df[self.label] / 1000 # 对于co，单位从μg/m³换算为mg/m³，防止目标数据跨越多个数量级，导致训练困难。AQI使用mg/m³或者ppm进行计算
        df.loc[:, self.label] = np.log(df[self.label] + self.log_increment)
        return df
    
    def train(self):
        data_files = glob.glob(os.path.join(self.data_path, self.label + "*.csv"))
        if not data_files:
            print(f"no data file found in {self.data_path}")
            return
        df = pd.DataFrame()
        for data_file in data_files:
            print(f"train data file: {data_file}")
            df = pd.concat([df,pd.read_csv(data_file)], ignore_index=True)
        df = self.before_train(df)
        print(f"total train data size: {len(df)}")
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=1)
        predictor = TabularPredictor(
            label=self.label,
            problem_type='regression',
            eval_metric="root_mean_squared_error",
            path=os.path.join(self.model_path, self.timestemp)
            ).fit(train_data=train_df,presets="best_quality")
        results = predictor.evaluate(test_df)
        evaluate_filename = "evaluate-" + self.label + "-" + str(len(df)) + "-" + self.timestemp + ".json"
        evaluate_filename = os.path.join(self.evaluate_path, evaluate_filename)
        with open(evaluate_filename, 'a') as file:
            json.dump(results, file)
        print(f"============================={self.label} evaluate result=====================================")
        print(results)

class AirQualityPredict:
    def __init__(self,model_path):
        self.model_path = model_path
        self.predictor = TabularPredictor.load(self.model_path)
    def predict(self,station,temp,wdsp,prcp,month):
        df = pd.DataFrame(columns=["STATION","TEMP","WDSP","PRCP","MONTH","pm25"])
        new_row = pd.DataFrame({'STATION': [station], 'TEMP': [temp],'WDSP': [wdsp],'PRCP': [prcp],'MONTH': [month],'pm25': [0.0]})
        df = pd.concat([df, new_row], ignore_index=True)
        predictions = self.predictor.predict(df)
        print("=============================predict result=====================================")
        print(predictions)
