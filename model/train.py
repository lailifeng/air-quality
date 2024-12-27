import pandas as pd
from sklearn.model_selection import train_test_split
from autogluon.tabular import TabularDataset, TabularPredictor


class AirQualityTrain:
    def __init__(self,label,data_file,model_path):
        self.label = label
        self.data_file = data_file
        self.model_path = model_path
    
    def train(self):
        df = pd.read_csv(self.data_file)
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=1)
        predictor = TabularPredictor(
            label=self.label,
            problem_type='regression',
            eval_metric="root_mean_squared_error",
            path=self.model_path
            ).fit(train_data=train_df,presets="best_quality")
        results = predictor.evaluate(test_df)
        print("=============================evaluate result=====================================")
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
