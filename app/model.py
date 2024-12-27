from autogluon.tabular import TabularDataset, TabularPredictor
import pandas as pd

class AirQualityPredictor:
    def __init__(self,model_path):
        self.model_path = model_path
        self.predictor = TabularPredictor.load(self.model_path)
    def predict(self,station,temp,wdsp,prcp,month):
        df = pd.DataFrame(columns=["STATION","TEMP","WDSP","PRCP","MONTH","pm25"])
        new_row = pd.DataFrame({'STATION': [station], 'TEMP': [temp],'WDSP': [wdsp],'PRCP': [prcp],'MONTH': [month],'pm25': [0.0]})
        df = pd.concat([df, new_row], ignore_index=True)
        predictions = self.predictor.predict(df)
        result =  predictions.values[0]
        print(f"predict value is {result}")
        return result