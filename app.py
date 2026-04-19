from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from predict import predict
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_bcrypt import Bcrypt
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"
bcrypt = Bcrypt(app)

# -------------------- الاتصال بقاعدة البيانات --------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# -------------------- تحديث السوق وإعادة تدريب النموذج --------------------
@app.route('/update_data')
def update_data():
    from scraper import scrape_data
    from retrain_model import retrain

    scrape_data()
    retrain()

    return "Market Data Updated & Model Retrained!"

# -------------------- إضافة عقار جديد --------------------
@app.route('/add_property', methods=['GET', 'POST'])
def add_property():
    if 'user_id' not in session or session['user_type'] != 'seller':
        return redirect(url_for('login'))

    if request.method == 'POST':
        seller_id = session['user_id']
        title = request.form['title']
        governorate = request.form['governorate']
        wilayat = request.form['wilayat']
        property_type = request.form['property_type']
        surface_area = float(request.form['surface_area'])
        bedrooms = int(request.form['bedrooms'])
        bathrooms = float(request.form['bathrooms'])
        floor = int(request.form['floor'])
        building_age = int(request.form['building_age'])
        furnishing = request.form['furnishing']
        price = float(request.form['price'])
        phone = request.form['phone']

        images_list = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            images_folder = os.path.join('static', 'images', 'properties')
            os.makedirs(images_folder, exist_ok=True)

            for file in files:
                if file.filename != '':
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(images_folder, filename))
                    images_list.append(filename)

        images_str = ','.join(images_list)

        cursor.execute("""
            INSERT INTO properties
            (seller_id, title, governorate, wilayat, property_type,
             surface_area, bedrooms, bathrooms, floor, building_age,
             furnishing, phone, price, images)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (seller_id, title, governorate, wilayat, property_type,
              surface_area, bedrooms, bathrooms, floor, building_age,
              furnishing, phone, price, images_str))

        conn.commit()
        return redirect(url_for('seller_dashboard'))

    return render_template('seller_add_property.html', username=session.get('name'))

# -------------------- تحرير الملف الشخصي --------------------
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor.execute("SELECT * FROM user_info WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']

        cursor.execute("""
            UPDATE user_info
            SET username=%s, email=%s, phone=%s
            WHERE id=%s
        """, (username, email, phone, user_id))

        conn.commit()
        return redirect(url_for('profile'))

    return render_template("edit_profile.html", user=user)

# -------------------- الصفحات العامة --------------------
@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/predictions')
def predictions():
    return render_template('predictions.html')

@app.route('/exploring')
def exploring():
    return render_template('exploring.html')

@app.route('/favorite')
def favorite():
    return render_template('favorite.html')

# -------------------- تسجيل المستخدم --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            user_type = request.form['user_type']

            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

            cursor.execute("""
                INSERT INTO users (name, email, password, user_type)
                VALUES (%s,%s,%s,%s)
            """, (name, email, hashed_password, user_type))

            conn.commit()
            return redirect('/login')

        except Exception as e:
            conn.rollback()
            print(e)
            return str(e)

    return render_template('register.html')

# -------------------- لوحة البائع --------------------
@app.route('/seller')
def seller_dashboard():
    if 'user_id' not in session or session['user_type'] != 'seller':
        return redirect(url_for('login'))

    seller_id = session['user_id']
    username = session.get('name', 'Seller')

    cursor.execute("SELECT COUNT(*) AS total FROM properties WHERE seller_id=%s", (seller_id,))
    total_properties = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) AS total_views
        FROM property_views pv
        JOIN properties p ON p.id = pv.property_id
        WHERE p.seller_id = %s
    """, (seller_id,))
    total_views = cursor.fetchone()['total_views']

    cursor.execute("""
        SELECT COUNT(*) AS total_favorite
        FROM favorite f
        JOIN properties p ON p.id = f.property_id
        WHERE p.seller_id = %s
    """, (seller_id,))
    total_favorite = cursor.fetchone()['total_favorite']

    cursor.execute("SELECT profile_image FROM user_info WHERE id=%s", (seller_id,))
    result_img = cursor.fetchone()
    profile_image = result_img['profile_image'] if result_img and result_img['profile_image'] else 'default.png'

    cursor.execute("SELECT * FROM properties WHERE seller_id=%s ORDER BY id DESC", (seller_id,))
    properties = cursor.fetchall()

    return render_template(
        "seller_dashboard.html",
        username=username,
        total_properties=total_properties,
        total_views=total_views,
        total_favorite=total_favorite,
        profile_image=profile_image,
        properties=properties
    )

# -------------------- لوحة المشتري --------------------
@app.route('/buyer')
def buyer_dashboard():
    if 'user_id' not in session or session['user_type'] != 'buyer':
        return redirect(url_for('login'))

    buyer_id = session['user_id']
    username = session.get('name', 'Buyer')

    cursor.execute("SELECT profile_image FROM user_info WHERE id=%s", (buyer_id,))
    result_img = cursor.fetchone()
    profile_image = result_img['profile_image'] if result_img and result_img['profile_image'] else 'default.png'

    cursor.execute("SELECT * FROM properties WHERE status='Available'")
    available_properties = cursor.fetchall()

    return render_template(
        "buyer_home.html",
        username=username,
        profile_image=profile_image,
        available_properties=available_properties,
        available_count=len(available_properties)
    )

# -------------------- تسجيل الدخول --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']
            session['name'] = user['name']

            if user['user_type'] == 'seller':
                return redirect(url_for('seller_dashboard'))
            elif user['user_type'] == 'buyer':
                return redirect(url_for('buyer_dashboard'))
            else:
                return redirect(url_for('admin_dashboard'))

        return "Email or Password incorrect"

    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

# -------------------- تشغيل التنبؤ --------------------
@app.route('/predict', methods=['POST'])
def make_prediction():
    try:
        age_map = {
            "Less than 1 year": 1,
            "1 - 3 years": 2,
            "4 - 6 years": 5,
            "7 - 10 years": 8,
            "More than 10 years": 12
        }

        raw_age = request.form.get("Building_Age")
        building_age = age_map.get(raw_age, 0)

        data = {
            "Governorate": request.form.get("Governorate"),
            "Wilayat": request.form.get("Wilayat"),
            "Property Type": request.form.get("Property_Type"),
            "Surface Area": float(request.form.get("Surface_Area", 0)),
            "Bedrooms": int(request.form.get("Bedrooms", 0)),
            "Bathrooms": float(request.form.get("Bathrooms", 0)),
            "Floor": int(request.form.get("Floor", 0)),
            "Building Age": building_age,
            "Furnishing": request.form.get("Furnishing")
        }

        price = float(predict(data))

        cursor.execute("""
            INSERT INTO market_data
            (governorate, wilayat, property_type, area, bedrooms,
             bathrooms, floor, building_age, furnishing, price)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["Governorate"], data["Wilayat"], data["Property Type"],
            data["Surface Area"], data["Bedrooms"], data["Bathrooms"],
            data["Floor"], data["Building Age"], data["Furnishing"], price
        ))

        conn.commit()

        return jsonify({"predicted_price": round(float(price), 2)})

    except Exception as e:
        conn.rollback()  # 🔥 مهم جداً
        return jsonify({"error": str(e)})

# -------------------- تشغيل السيرفر --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))