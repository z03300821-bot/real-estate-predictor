# retrain.py
import pandas as pd
import mysql.connector
import pickle
from sklearn.ensemble import RandomForestRegressor

def retrain():
    # الاتصال بقاعدة البيانات
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="real_estate_vision"
    )

    # سحب البيانات من جدول market_data
    df = pd.read_sql("SELECT property_type, area, bedrooms, bathrooms, governorate, wilayat, floor, building_age, price FROM market_data", db)

    # التأكد من القيم الفارغة
    df['area'].fillna(df['area'].median(), inplace=True)
    df['bedrooms'].fillna(0, inplace=True)
    df['bathrooms'].fillna(0, inplace=True)
    df['floor'].fillna(0, inplace=True)
    df['building_age'].fillna(0, inplace=True)
    df.dropna(subset=['price'], inplace=True)

    # تحويل الأعمدة النصية إلى dummies
    df = pd.get_dummies(df, columns=['property_type', 'governorate', 'wilayat', 'building_age'], drop_first=True)

    # فصل X و y
    X = df.drop('price', axis=1)
    y = df['price']

    # تدريب Random Forest
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X, y)

    # حفظ النموذج وأسماء الأعمدة
    with open("model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open("columns.pkl", "wb") as f:
        pickle.dump(X.columns.tolist(), f)

    db.close()
    print("Model retrained with all property features successfully!")