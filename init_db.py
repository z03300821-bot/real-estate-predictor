import psycopg2
import os

DATABASE_URL = "postgresql://realestate_db_429j_user:UzRxf2NzoLIQIdZlxJtrvo7SycCoTTq0@dpg-d7huasugvqtc738tuueg-a.oregon-postgres.render.com/realestate_db_429j"

conn = psycopg2.connect(DATABASE_URL)

cursor = conn.cursor()

print("Connected successfully!")

# ---------------- USERS ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT,
    user_type TEXT
);
""")

# ---------------- PROPERTIES ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS properties (
    id SERIAL PRIMARY KEY,
    seller_id INT,
    title TEXT,
    governorate TEXT,
    wilayat TEXT,
    property_type TEXT,
    surface_area FLOAT,
    bedrooms INT,
    bathrooms FLOAT,
    floor INT,
    building_age INT,
    furnishing TEXT,
    phone TEXT,
    price FLOAT,
    images TEXT
);
""")

# ---------------- FAVORITES ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS favorites (
    id SERIAL PRIMARY KEY,
    user_id INT,
    property_id INT
);
""")

# ---------------- PROPERTY IMAGES ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS property_images (
    id SERIAL PRIMARY KEY,
    property_id INT,
    image TEXT
);
""")

# ---------------- MARKET DATA ----------------
cursor.execute("""
CREATE TABLE IF NOT EXISTS market_data (
    id SERIAL PRIMARY KEY,
    governorate TEXT,
    wilayat TEXT,
    property_type TEXT,
    area FLOAT,
    bedrooms INT,
    bathrooms FLOAT,
    floor INT,
    building_age INT,
    furnishing TEXT,
    price FLOAT
);
""")

conn.commit()
cursor.close()
conn.close()

print("Database initialized successfully!")