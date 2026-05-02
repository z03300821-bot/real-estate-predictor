from flask import Flask, render_template, request, redirect, session, jsonify, url_for
from predict import predict
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_bcrypt import Bcrypt
import os

app = Flask(__name__)
app.secret_key = "secret123"
bcrypt = Bcrypt(app)

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    return conn, cursor


# ---------------- HOME ----------------
@app.route('/')
def homepage():
    return render_template('homepage.html')


# ---------------- REGISTER ----------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        conn, cursor = get_db()

        cursor.execute("""
            INSERT INTO users (name, email, password, user_type)
            VALUES (%s,%s,%s,%s)
        """, (
            request.form['name'],
            request.form['email'],
            bcrypt.generate_password_hash(request.form['password']).decode('utf-8'),
            request.form['user_type']
        ))

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('register.html')


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn, cursor = get_db()

        cursor.execute("SELECT * FROM users WHERE email=%s", (request.form['email'],))
        user = cursor.fetchone()

        conn.close()

        if user and bcrypt.check_password_hash(user['password'], request.form['password']):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['user_type'] = user['user_type']

            return redirect('/seller' if user['user_type'] == 'seller' else '/buyer')

        return "Invalid login"

    return render_template('login.html')


# ---------------- LOGOUT (FIXED) ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------- SELLER ----------------
@app.route('/seller')
def seller_dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn, cursor = get_db()

    cursor.execute("SELECT * FROM properties WHERE seller_id=%s", (session['user_id'],))
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


# ---------------- BUYER ----------------
@app.route('/buyer')
def buyer_dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn, cursor = get_db()
    cursor.execute("SELECT * FROM properties")
    properties = cursor.fetchall()
    conn.close()

    return render_template("buyer_home.html", properties=properties)


# ---------------- ADD PROPERTY ----------------
@app.route('/add_property', methods=['GET', 'POST'])
def add_property():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        conn, cursor = get_db()

        cursor.execute("""
            INSERT INTO properties (seller_id, title, price)
            VALUES (%s,%s,%s)
        """, (
            session['user_id'],
            request.form['title'],
            request.form['price']
        ))

        conn.commit()
        conn.close()

        return redirect('/seller')

    return render_template('seller_add_property.html')

@app.route('/exploring')
def exploring():
    return render_template('exploring.html')

@app.route('/predictions')
def predictions():
    return render_template('predictions.html')


# ---------------- PREDICT ----------------
@app.route('/predict', methods=['POST'])
def make_prediction():
    try:
        data = {
            "Governorate": request.form.get("Governorate"),
            "Wilayat": request.form.get("Wilayat"),
            "Surface Area": float(request.form.get("Surface_Area", 0)),
        }

        price = float(predict(data))

        conn, cursor = get_db()
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


if __name__ == "__main__":
    app.run()