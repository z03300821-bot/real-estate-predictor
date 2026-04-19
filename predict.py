#predict.py
import joblib
import pandas as pd

def predict(data_dict):
    df = pd.DataFrame([data_dict])

    # تحويل النصوص إلى dummies كما في التدريب
    df = pd.get_dummies(
        df,
        columns=[
            "Property Type",
            "Bedrooms",
            "Bathrooms",
            "Furnishing",
            "Building Age",
            "Governorate",
            "Wilayat"
        ],
        drop_first=True
    )

    # تنظيف أسماء الأعمدة
    df.columns = df.columns.str.replace('[^A-Za-z0-9_]', '_', regex=True)

    # تحميل الأعمدة من التدريب
    cols = joblib.load("columns.pkl")

    # إضافة أي أعمدة مفقودة وتعويضها بـ 0
    for col in cols:
        if col not in df.columns:
            df[col] = 0

    # ترتيب الأعمدة كما في التدريب
    df = df[cols]

    # تحميل النموذج والتنبؤ
    model = joblib.load("model.pkl")
    prediction = model.predict(df)[0]

    return float(prediction)