#evaluation.py
import pandas as pd
import joblib
from sklearn.metrics import mean_absolute_error, r2_score

# 1️⃣ تحميل بيانات الاختبار
X_test = pd.read_csv("data/X_test.csv")
y_test = pd.read_csv("data/y_test.csv").squeeze()

# 2️⃣ تحميل النموذج وأسماء الأعمدة
model = joblib.load("model.pkl")
cols = joblib.load("columns.pkl")

# 3️⃣ ضبط الأعمدة لتطابق التدريب
for col in cols:
    if col not in X_test.columns:
        X_test[col] = 0
X_test = X_test[cols]

# 4️⃣ التنبؤ
y_pred = model.predict(X_test)

# 5️⃣ حساب مؤشرات الأداء
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("MAE:", mae)
print("R²:", r2)

