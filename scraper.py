# scraper.py 
import requests
from bs4 import BeautifulSoup
import mysql.connector
import re

# دوال تنظيف البيانات
def clean_price(price_text):
    price = re.sub(r"[^\d.]", "", price_text)
    return float(price) if price else None

def clean_area(area_text):
    area = re.sub(r"[^\d.]", "", area_text)
    return float(area) if area else None

def scrape_data():
    url = "https://om.opensooq.com/ar/عقارات/عقارات-للبيع"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    # الاتصال بقاعدة البيانات
    db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="real_estate"
    )
    cursor = db.cursor()

    # حذف البيانات القديمة
    cursor.execute("DELETE FROM market_data")
    db.commit()

    # طلب الصفحة
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    # كل الإعلانات
    listings = soup.find_all("div", class_="postItem")

    for item in listings:

        # السعر
        price_tag = item.find("span")
        if price_tag:
            inner_span = price_tag.find("span")
            price = clean_price(inner_span.text) if inner_span else None
        else:
            price = None

        # المساحة
        area_tag = item.find("a", text=lambda x: x and "م²" in x)
        area = clean_area(area_tag.text) if area_tag else None

        # عدد الغرف
        bedrooms = None
        for li in item.find_all("li"):
            span = li.find("span")
            if span and "عدد الغرف" in span.text:
                a_tag = li.find("a")
                if a_tag:
                    try:
                        bedrooms = int(a_tag.text)
                    except:
                        bedrooms = None

        # عدد الحمامات
        bathrooms = None
        for li in item.find_all("li"):
            span = li.find("span")
            if span and "عدد الحمامات" in span.text:
                a_tag = li.find("a")
                if a_tag:
                    try:
                        bathrooms = int(a_tag.text)
                    except:
                        bathrooms = None

        # المحافظة / المدينة
        governorate = None
        for li in item.find_all("li"):
            span = li.find("span")
            if span and "المدينة" in span.text:
                a_tag = li.find("a")
                if a_tag:
                    governorate = a_tag.text

        # الحي / Neighborhood
        neighborhood = None
        for li in item.find_all("li"):
            span = li.find("span")
            if span and "الحي" in span.text:
                a_tag = li.find("a")
                if a_tag:
                    neighborhood = a_tag.text

        # الطابق
        floor = None
        for li in item.find_all("li"):
            span = li.find("span")
            if span and "الطابق" in span.text:
                a_tag = li.find("a")
                if a_tag:
                    text = a_tag.text
                    floor = 0
                    if "الأول" in text: floor = 1
                    elif "الثاني" in text: floor = 2
                    elif "الثالث" in text: floor = 3
                    elif "الرابع" in text: floor = 4
                    elif "الخامس" in text: floor = 5
                    elif "السادس" in text: floor = 6
                    elif "السابع" in text: floor = 7
                    elif "الثامن" in text: floor = 8

        # عمر البناء
        age_building = None
        for li in item.find_all("li"):
            span = li.find("span")
            if span and "عمر البناء" in span.text:
                a_tag = li.find("a")
                if a_tag:
                    text = a_tag.text.strip()
                    if text == "قيد الإنشاء":
                        age_building = 0
                    elif text == "جديد":
                        age_building = 1
                    else:
                        match = re.search(r'\d+', text)
                        if match:
                            age_building = int(match.group())

        # نوع العقار من الإعلان
        property_type = "Unknown"
        type_tag = item.find("a", class_="has-color")
        if type_tag:
            text = type_tag.text.strip()
            if "شقق" in text:
                property_type = "Apartment"
            elif "فلل" in text:
                property_type = "Villa"
            elif "توين فلل" in text:
                property_type = "Twin Villa"

        # إدخال البيانات في قاعدة البيانات
        cursor.execute("""
            INSERT INTO market_data
            (property_type, area, bedrooms, bathrooms, governorate, neighborhood, floor, building_age, price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (property_type, area, bedrooms, bathrooms, governorate, neighborhood, floor, age_building, price))

    db.commit()
    db.close()
    print("Market Data Updated Successfully!")