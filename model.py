# model.py
from sklearn.ensemble import RandomForestRegressor

def build_model():
    # Random Forest مع 200 شجرة
    model = RandomForestRegressor(
        n_estimators=200,
        random_state=42
    )
    return model
