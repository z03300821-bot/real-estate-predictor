#app.py
from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from predict import predict
import mysql.connector
from flask_bcrypt import Bcrypt
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"
bcrypt = Bcrypt(app)

# -------------------- الاتصال بقاعدة البيانات --------------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="real_estate_vision"
)
cursor = db.cursor(dictionary=True)

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

        # رفع الصور
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
            (seller_id, title, governorate, wilayat, property_type, surface_area, bedrooms, bathrooms, floor, building_age, furnishing, phone, price, images)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (seller_id, title, governorate, wilayat, property_type, surface_area, bedrooms, bathrooms, floor, building_age, furnishing, phone, price, images_str))
        db.commit()

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
        db.commit()
        return redirect(url_for('profile'))

    return render_template("edit_profile.html", user=user)

# -------------------- صفحات عامة --------------------
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
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        user_type = request.form['user_type']

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        cursor.execute(
            "INSERT INTO users (name, email, password, user_type) VALUES (%s,%s,%s,%s)",
            (name, email, hashed_password, user_type)
        )
        db.commit()
        return redirect('/login')

    return render_template('register.html')

# -------------------- لوحة البائع --------------------
@app.route('/seller')
def seller_dashboard():
    if 'user_id' not in session or session['user_type'] != 'seller':
        return redirect(url_for('login'))
    
    seller_id = session['user_id']
    username = session.get('name', 'Seller')

    cursor = db.cursor(dictionary=True)

    # Total Properties
    cursor.execute("SELECT COUNT(*) AS total FROM properties WHERE seller_id = %s", (seller_id,))
    result = cursor.fetchone()
    total_properties = result['total'] if result else 0

    # Total Views
    cursor.execute("""
        SELECT COUNT(*) AS total_views
        FROM property_views pv
        JOIN properties p ON p.id = pv.property_id
        WHERE p.seller_id = %s
    """, (seller_id,))
    result_views = cursor.fetchone()
    total_views = result_views['total_views'] if result_views else 0

    # Total favorite
    cursor.execute("""
        SELECT COUNT(*) AS total_favorite
        FROM favorite f
        JOIN properties p ON p.id = f.property_id
        WHERE p.seller_id = %s
    """, (seller_id,))
    result_fav = cursor.fetchone()
    total_favorite = result_fav['total_favorite'] if result_fav else 0

    # Profile Image
    cursor.execute("SELECT profile_image FROM user_info WHERE id = %s", (seller_id,))
    result_img = cursor.fetchone()
    profile_image = result_img['profile_image'] if result_img and result_img['profile_image'] else 'default.png'
    
    # ------------------- جلب العقارات -------------------
    cursor.execute("SELECT * FROM properties WHERE seller_id = %s ORDER BY id DESC", (seller_id,))
    properties = cursor.fetchall()  # قائمة العقارات
    
    print("DEBUG IMAGE:", profile_image)
    print("DEBUG PROPERTIES:", properties)

    return render_template(
        "seller_dashboard.html",
        username=username,
        total_properties=total_properties,
        total_views=total_views,
        total_favorite=total_favorite,
        profile_image=profile_image,
        properties=properties  # أرسلها للقالب
    )

@app.route('/my_listings')
def my_listings():
    if 'user_id' not in session or session['user_type'] != 'seller':
        return redirect(url_for('login'))

    seller_id = session['user_id']
    cursor.execute("SELECT * FROM properties WHERE seller_id=%s", (seller_id,))
    properties = cursor.fetchall()

    for prop in properties:
        if 'status' not in prop or not prop['status']:
            prop['status'] = 'Available'

    return render_template('seller_my_listings.html', properties=properties, username=session.get('name'))

# -------------------- تحرير وحذف العقارات --------------------
@app.route('/edit_property/<int:property_id>', methods=['GET', 'POST'])
def edit_property(property_id):
    if 'user_id' not in session or session['user_type'] != 'seller':
        return redirect(url_for('login'))

    cursor.execute("SELECT * FROM properties WHERE id=%s AND seller_id=%s",
                   (property_id, session['user_id']))
    property = cursor.fetchone()

    if request.method == 'POST':
        cursor.execute("""
            UPDATE properties
            SET title=%s, price=%s, governorate=%s, wilayat=%s, property_type=%s
            WHERE id=%s AND seller_id=%s
        """, (
            request.form['title'],
            request.form['price'],
            request.form['governorate'],
            request.form['wilayat'],
            request.form['property_type'],
            property_id,
            session['user_id']
        ))
        db.commit()
        return redirect(url_for('my_listings'))

    return render_template('seller_edit_property.html', property=property)

@app.route('/delete_property/<int:property_id>', methods=['POST'])
def delete_property(property_id):
    if 'user_id' not in session or session['user_type'] != 'seller':
        return redirect(url_for('login'))

    cursor.execute(
        "DELETE FROM properties WHERE id=%s AND seller_id=%s",
        (property_id, session['user_id'])
    )
    db.commit()
    return redirect(url_for('my_listings'))

# -------------------- لوحة المشتري --------------------
@app.route('/buyer')
def buyer_dashboard():
    if 'user_id' not in session or session['user_type'] != 'buyer':
        return redirect(url_for('login'))

    buyer_id = session['user_id']
    username = session.get('name', 'Buyer')

    cursor = db.cursor(dictionary=True)

    # Profile Image
    cursor.execute("SELECT profile_image FROM user_info WHERE id = %s", (buyer_id,))
    result_img = cursor.fetchone()
    profile_image = result_img['profile_image'] if result_img and result_img['profile_image'] else 'default.png'

    # Available Properties (all sellers' properties with status='Available')
    cursor.execute("SELECT * FROM properties WHERE status='Available'")
    available_properties = cursor.fetchall()
    available_count = len(available_properties)



    return render_template(
        "buyer_home.html",
        username=username,
        profile_image=profile_image,
        available_properties=available_properties,
        available_count=available_count,
    
    )

# -------------------- لوحة الأدمن --------------------
@app.route('/admin')
def admin_dashboard():
    if session.get('user_role') != 'admin':
        return "Access Denied", 403
    return render_template('admin_dashboard.html')

# -------------------- تسجيل الدخول --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_type_from_form = request.form.get('user_type')  # هذا المهم

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']  # من قاعدة البيانات
            session['name'] = user['name']

            # Redirect حسب نوع المستخدم
            if user['user_type'] == 'seller':
                return redirect(url_for('seller_dashboard'))
            elif user['user_type'] == 'buyer':
                return redirect(url_for('buyer_dashboard'))
            elif user['user_type'] == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            return "Email or Password incorrect"

    # لو GET → عرض الصفحة
    return render_template('login.html')

# -------------------- الملف الشخصي --------------------
# -------------------- الملف الشخصي --------------------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cursor.execute("SELECT * FROM user_info WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']

        profile_image = None
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            if file.filename != '':
                filename = secure_filename(file.filename)
                folder = os.path.join('static', 'images', 'profiles')
                os.makedirs(folder, exist_ok=True)
                file.save(os.path.join(folder, filename))
                profile_image = filename

        if user:
            # تحديث فقط إذا الصف موجود
            if profile_image:
                cursor.execute("""
                    UPDATE user_info
                    SET username=%s, email=%s, phone=%s, profile_image=%s
                    WHERE id=%s
                """, (username, email, phone, profile_image, user_id))
            else:
                cursor.execute("""
                    UPDATE user_info
                    SET username=%s, email=%s, phone=%s
                    WHERE id=%s
                """, (username, email, phone, user_id))
        else:
            # المستخدم جديد → إنشاء صف جديد
            cursor.execute("""
                INSERT INTO user_info (id, username, email, phone, profile_image)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, username, email, phone, profile_image or 'default.png'))

        db.commit()
        return redirect(url_for('profile'))

    # هذا السطر يُنفذ فقط عند GET
    return render_template('profile.html', **(user or {}))
@app.route('/signup')
def signup():
    return render_template('signup.html')

# -------------------- تسجيل الخروج --------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('homepage'))



# -------------------- التنبؤ وحفظه في قاعدة البيانات --------------------
# -------------------- التنبؤ وحفظه في قاعدة البيانات --------------------
@app.route('/predict', methods=['POST'])
def make_prediction():
    try:
        # تحويل كل القيم الرقمية بشكل صحيح
        surface_area = float(request.form.get("Surface_Area", 0))
        bedrooms = int(request.form.get("Bedrooms", 0))
        bathrooms = float(request.form.get("Bathrooms", 0))
        floor = int(request.form.get("Floor", 0))

        # هذا مهم: تحويل building_age مع التعامل مع القيم الفارغة
        building_age_raw = request.form.get("Building_Age", 0)
        try:
            building_age = int(building_age_raw)
        except:
            building_age = 0

        data = {
            "Governorate": request.form.get("Governorate"),
            "Wilayat": request.form.get("Wilayat"),
            "Property Type": request.form.get("Property_Type"),
            "Surface Area": surface_area,
            "Bedrooms": bedrooms,
            "Bathrooms": bathrooms,
            "Floor": floor,
            "Building Age": building_age,
            "Furnishing": request.form.get("Furnishing")
        }

        # التنبؤ بالسعر
        price = predict(data)

        # حفظ البيانات في جدول market_data
        cursor.execute("""
            INSERT INTO market_data
            (governorate, wilayat, property_type, area, bedrooms, bathrooms, floor, building_age, furnishing, price)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            data["Governorate"],
            data["Wilayat"],
            data["Property Type"],
            data["Surface Area"],
            data["Bedrooms"],
            data["Bathrooms"],
            data["Floor"],
            data["Building Age"],
            data["Furnishing"],
            price
        ))
        db.commit()

        return jsonify({"predicted_price": round(float(price), 2)})

    except Exception as e:
        return jsonify({"error": str(e)})
    
@app.route('/add_favorite/<int:property_id>', methods=['POST'])
def add_favorite(property_id):
    if 'user_id' not in session or session['user_type'] != 'buyer':
        return redirect(url_for('login'))

    buyer_id = session['user_id']

    # تأكد أنه لم يضف العقار مسبقًا
    cursor.execute("SELECT * FROM favorite WHERE user_id=%s AND property_id=%s", (buyer_id, property_id))
    existing = cursor.fetchone()
    if not existing:
        cursor.execute("INSERT INTO favorite (user_id, property_id) VALUES (%s, %s)", (buyer_id, property_id))
        db.commit()

    return redirect(url_for('buyer_dashboard'))

# -------------------- تشغيل السيرفر --------------------
if __name__ == "__main__":
    app.run(debug=True)