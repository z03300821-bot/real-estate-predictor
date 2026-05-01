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

# -------------------- DATABASE --------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise Exception("DATABASE_URL not found in environment variables")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)


# 🔥 FIX IMPORTANT: create new connection each request
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    return conn, cursor

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# -------------------- HOME --------------------
@app.route('/')
def homepage():
    return render_template('homepage.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/predictions')
def predictions():
    return render_template('predictions.html')

@app.route('/exploring')
def exploring():
    return render_template('exploring.html')

@app.route('/favorite')
def favorite():
    return render_template('favorite.html')


# -------------------- REGISTER --------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            conn, cursor = get_db()

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
            conn.close()

            return redirect('/login')

        except Exception as e:
            return str(e)

    return render_template('register.html')


# -------------------- LOGIN --------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn, cursor = get_db()

        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()

        conn.close()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_type'] = user['user_type']
            session['name'] = user['name']

            if user['user_type'] == 'seller':
                return redirect(url_for('seller_dashboard'))
            else:
                return redirect(url_for('buyer_dashboard'))

        return "Email or Password incorrect"

    return render_template('login.html')


# -------------------- SELLER --------------------
@app.route('/seller')
def seller_dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn, cursor = get_db()
    seller_id = session['user_id']

    cursor.execute("SELECT * FROM properties WHERE seller_id=%s", (seller_id,))
    properties = cursor.fetchall()

    conn.close()

    return render_template(
        "seller_dashboard.html",
        properties=properties,
        username=session.get('name'),
        total_properties=len(properties),
        total_views=0,
        total_favorites=0,
        profile_image="default.png"
    )


# -------------------- BUYER --------------------
@app.route('/buyer')
def buyer_dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn, cursor = get_db()

    cursor.execute("SELECT * FROM properties WHERE status='Available'")
    properties = cursor.fetchall()

    conn.close()

    return render_template("buyer_home.html", available_properties=properties)


# -------------------- ADD PROPERTY --------------------
@app.route('/add_property', methods=['GET', 'POST'])
def add_property():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        conn, cursor = get_db()

        seller_id = session['user_id']
        title = request.form['title']
        price = request.form['price']

        cursor.execute("""
            INSERT INTO properties (seller_id, title, price)
            VALUES (%s,%s,%s)
        """, (seller_id, title, price))

        conn.commit()
        conn.close()

        return redirect('/seller')

    return render_template('seller_add_property.html')


# -------------------- PROFILE --------------------
@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect('/login')

    conn, cursor = get_db()
    user_id = session['user_id']

    cursor.execute("SELECT * FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    conn.close()

    return render_template("edit_profile.html", user=user)


# -------------------- PREDICT --------------------
@app.route('/predict', methods=['POST'])
def make_prediction():
    try:
        conn, cursor = get_db()

        data = {
            "Governorate": request.form.get("Governorate"),
            "Wilayat": request.form.get("Wilayat"),
            "Surface Area": float(request.form.get("Surface_Area", 0)),
        }

        price = float(predict(data))

        cursor.execute("""
            INSERT INTO market_data (governorate, wilayat, area, price)
            VALUES (%s,%s,%s,%s)
        """, (
            data["Governorate"],
            data["Wilayat"],
            data["Surface Area"],
            price
        ))

        conn.commit()
        conn.close()

        return jsonify({"predicted_price": price})

    except Exception as e:
        return jsonify({"error": str(e)})


# -------------------- RUN --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))