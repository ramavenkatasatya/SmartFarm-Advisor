import os
import sqlite3
import json
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.parse import urlencode

from flask import Flask, render_template, request, redirect, url_for, jsonify

from services.ml_prediction import predict_crops
from services.advisory_engine import generate_advisory


# =========================================================
# APPLICATION CONFIGURATION
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Vercel filesystem is read-only except /tmp.
if os.environ.get("VERCEL"):
    DATABASE_PATH = "/tmp/smartfarm.db"
else:
    DATABASE_DIR = os.path.join(BASE_DIR, "database")
    os.makedirs(DATABASE_DIR, exist_ok=True)
    DATABASE_PATH = os.path.join(DATABASE_DIR, "smartfarm.db")


app = Flask(__name__)


# =========================================================
# DATABASE
# =========================================================

def get_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def column_exists(connection, table_name, column_name):
    columns = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(row["name"] == column_name for row in columns)


def add_column_if_missing(connection, table_name, column_name, definition):

    if not column_exists(
        connection,
        table_name,
        column_name
    ):
        connection.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name} {definition}
            """
        )


def init_db():

    connection = get_db()

    # -----------------------------------------------------
    # ADVISORY HISTORY
    # -----------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS advisory_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT,

            nitrogen REAL,
            phosphorus REAL,
            potassium REAL,

            temperature REAL,
            humidity REAL,
            ph REAL,
            rainfall REAL,

            recommended_crop TEXT,
            confidence REAL,

            irrigation TEXT,
            fertilizer TEXT,
            soil_advice TEXT,
            general_advice TEXT
        )
    """)

    # -----------------------------------------------------
    # FARM PROFILE
    # -----------------------------------------------------

    connection.execute("""
        CREATE TABLE IF NOT EXISTS farm_profile (
            id INTEGER PRIMARY KEY,

            farmer_name TEXT,
            farm_name TEXT,

            area REAL,

            village TEXT,
            district TEXT,
            state TEXT,

            soil_type TEXT,

            irrigation_type TEXT,
            water_availability TEXT,

            current_crop TEXT,
            sowing_date TEXT,

            latitude REAL,
            longitude REAL,
            location_accuracy REAL,
            location_name TEXT,

            weather_temperature REAL,
            weather_humidity REAL,
            weather_rainfall REAL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # -----------------------------------------------------
    # MIGRATION FOR EXISTING DATABASES
    # -----------------------------------------------------

    add_column_if_missing(
        connection,
        "farm_profile",
        "latitude",
        "REAL"
    )

    add_column_if_missing(
        connection,
        "farm_profile",
        "longitude",
        "REAL"
    )

    add_column_if_missing(
        connection,
        "farm_profile",
        "location_accuracy",
        "REAL"
    )

    add_column_if_missing(
        connection,
        "farm_profile",
        "location_name",
        "TEXT"
    )

    add_column_if_missing(
        connection,
        "farm_profile",
        "weather_temperature",
        "REAL"
    )

    add_column_if_missing(
        connection,
        "farm_profile",
        "weather_humidity",
        "REAL"
    )

    add_column_if_missing(
        connection,
        "farm_profile",
        "weather_rainfall",
        "REAL"
    )

    connection.commit()
    connection.close()


# Initialize database
init_db()


# =========================================================
# EXTERNAL API HELPERS
# =========================================================

def reverse_geocode(latitude, longitude):

    """
    Convert latitude/longitude into a readable location
    using OpenStreetMap Nominatim.
    """

    params = urlencode({
        "lat": latitude,
        "lon": longitude,
        "format": "jsonv2",
        "zoom": 10,
        "addressdetails": 1
    })

    url = (
        "https://nominatim.openstreetmap.org/reverse?"
        + params
    )

    request = Request(
        url,
        headers={
            "User-Agent":
                "SmartFarm-Advisor/1.0 "
                "(agricultural-advisory-project)"
        }
    )

    with urlopen(request, timeout=10) as response:

        data = json.loads(
            response.read().decode("utf-8")
        )

    address = data.get("address", {})

    location_name = (
        address.get("village")
        or address.get("town")
        or address.get("city")
        or address.get("municipality")
        or address.get("county")
        or "Unknown location"
    )

    district = (
        address.get("state_district")
        or address.get("district")
        or address.get("county")
        or ""
    )

    state = address.get("state", "")
    country = address.get("country", "")

    return {
        "location_name": location_name,
        "district": district,
        "state": state,
        "country": country,
        "display_name": data.get(
            "display_name",
            location_name
        )
    }


def get_weather(latitude, longitude):

    """
    Get current weather and recent/future precipitation
    from Open-Meteo.
    """

    params = urlencode({
        "latitude": latitude,
        "longitude": longitude,

        "current": (
            "temperature_2m,"
            "relative_humidity_2m,"
            "precipitation"
        ),

        "daily": (
            "precipitation_sum,"
            "temperature_2m_max,"
            "temperature_2m_min"
        ),

        "forecast_days": 7,

        "timezone": "auto"
    })

    url = (
        "https://api.open-meteo.com/v1/forecast?"
        + params
    )

    request = Request(
        url,
        headers={
            "User-Agent":
                "SmartFarm-Advisor/1.0"
        }
    )

    with urlopen(request, timeout=10) as response:

        data = json.loads(
            response.read().decode("utf-8")
        )

    current = data.get("current", {})
    daily = data.get("daily", {})

    temperature = current.get(
        "temperature_2m"
    )

    humidity = current.get(
        "relative_humidity_2m"
    )

    current_precipitation = current.get(
        "precipitation",
        0
    )

    daily_rainfall = daily.get(
        "precipitation_sum",
        []
    )

    # Seven-day rainfall total.
    forecast_rainfall = sum(
        float(value or 0)
        for value in daily_rainfall
    )

    return {
        "temperature": temperature,
        "humidity": humidity,

        # Use 7-day accumulated precipitation
        # as the rainfall signal for the advisor.
        "rainfall": forecast_rainfall,

        "current_precipitation":
            current_precipitation,

        "daily_rainfall":
            daily_rainfall
    }


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():
    return render_template("index.html")


# =========================================================
# CROP ADVISOR
# =========================================================

@app.route("/advisor")
def advisor():
    return render_template("advisor.html")


# =========================================================
# LOCATION PAGE
# =========================================================

@app.route("/location")
def location():

    connection = get_db()

    profile = connection.execute("""
        SELECT *
        FROM farm_profile
        WHERE id = 1
    """).fetchone()

    connection.close()

    return render_template(
        "location.html",
        profile=profile
    )


# =========================================================
# LOCATION API
# =========================================================

@app.route(
    "/api/location",
    methods=["POST"]
)
def save_location():

    try:

        data = request.get_json(
            silent=True
        ) or {}

        latitude = float(
            data.get("latitude")
        )

        longitude = float(
            data.get("longitude")
        )

        accuracy_raw = data.get(
            "accuracy"
        )

        accuracy = (
            float(accuracy_raw)
            if accuracy_raw is not None
            else None
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "status": "error",
            "message":
                "Invalid location coordinates."
        }), 400

    # -----------------------------------------------------
    # VALIDATE COORDINATES
    # -----------------------------------------------------

    if not -90 <= latitude <= 90:

        return jsonify({
            "status": "error",
            "message": "Invalid latitude."
        }), 400

    if not -180 <= longitude <= 180:

        return jsonify({
            "status": "error",
            "message": "Invalid longitude."
        }), 400

    try:

        # -------------------------------------------------
        # REVERSE GEOCODING
        # -------------------------------------------------

        location_data = reverse_geocode(
            latitude,
            longitude
        )

    except Exception as error:

        print(
            "Reverse geocoding error:",
            error
        )

        location_data = {
            "location_name":
                "Location detected",
            "district": "",
            "state": "",
            "country": "",
            "display_name":
                "Location detected"
        }

    try:

        # -------------------------------------------------
        # WEATHER
        # -------------------------------------------------

        weather = get_weather(
            latitude,
            longitude
        )

    except Exception as error:

        print(
            "Weather API error:",
            error
        )

        weather = {
            "temperature": None,
            "humidity": None,
            "rainfall": None,
            "current_precipitation": None,
            "daily_rainfall": []
        }

    # -----------------------------------------------------
    # SAVE TO FARM PROFILE
    # -----------------------------------------------------

    connection = get_db()

    # Make sure profile row exists.
    connection.execute("""
        INSERT OR IGNORE INTO farm_profile (
            id
        )
        VALUES (1)
    """)

    connection.execute("""
        UPDATE farm_profile

        SET
            latitude = ?,
            longitude = ?,
            location_accuracy = ?,
            location_name = ?,

            district = CASE
                WHEN ? != ''
                THEN ?
                ELSE district
            END,

            state = CASE
                WHEN ? != ''
                THEN ?
                ELSE state
            END,

            weather_temperature = ?,
            weather_humidity = ?,
            weather_rainfall = ?,

            updated_at = CURRENT_TIMESTAMP

        WHERE id = 1
    """, (

        latitude,
        longitude,
        accuracy,

        location_data["location_name"],

        location_data["district"],
        location_data["district"],

        location_data["state"],
        location_data["state"],

        weather["temperature"],
        weather["humidity"],
        weather["rainfall"]
    ))

    connection.commit()
    connection.close()

    return jsonify({

        "status": "ok",

        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,

            "name":
                location_data["location_name"],

            "district":
                location_data["district"],

            "state":
                location_data["state"],

            "country":
                location_data["country"],

            "display_name":
                location_data["display_name"]
        },

        "weather": weather
    })


# =========================================================
# WEATHER API
# =========================================================

@app.route("/api/weather")
def weather_api():

    try:

        latitude = float(
            request.args.get(
                "latitude"
            )
        )

        longitude = float(
            request.args.get(
                "longitude"
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return jsonify({
            "status": "error",
            "message":
                "Latitude and longitude are required."
        }), 400

    try:

        weather = get_weather(
            latitude,
            longitude
        )

        return jsonify({
            "status": "ok",
            "weather": weather
        })

    except Exception as error:

        print(
            "Weather error:",
            error
        )

        return jsonify({
            "status": "error",
            "message":
                "Unable to retrieve weather data."
        }), 500


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    connection = get_db()

    latest = connection.execute("""
        SELECT *
        FROM advisory_history
        ORDER BY id DESC
        LIMIT 1
    """).fetchone()

    total_advisories = connection.execute("""
        SELECT COUNT(*) AS count
        FROM advisory_history
    """).fetchone()["count"]

    farm_profile = connection.execute("""
        SELECT *
        FROM farm_profile
        WHERE id = 1
    """).fetchone()

    connection.close()

    return render_template(
        "dashboard.html",
        latest=latest,
        total_advisories=total_advisories,
        farm_profile=farm_profile
    )


# =========================================================
# MY FARM
# =========================================================

@app.route(
    "/my-farm",
    methods=["GET", "POST"]
)
def my_farm():

    connection = get_db()

    if request.method == "POST":

        farmer_name = request.form.get(
            "farmer_name",
            ""
        ).strip()

        farm_name = request.form.get(
            "farm_name",
            ""
        ).strip()

        area_raw = request.form.get(
            "area",
            ""
        ).strip()

        village = request.form.get(
            "village",
            ""
        ).strip()

        district = request.form.get(
            "district",
            ""
        ).strip()

        state = request.form.get(
            "state",
            ""
        ).strip()

        soil_type = request.form.get(
            "soil_type",
            ""
        ).strip()

        irrigation_type = request.form.get(
            "irrigation_type",
            ""
        ).strip()

        water_availability = request.form.get(
            "water_availability",
            ""
        ).strip()

        current_crop = request.form.get(
            "current_crop",
            ""
        ).strip()

        sowing_date = request.form.get(
            "sowing_date",
            ""
        ).strip()

        try:

            area = float(area_raw)

            if area <= 0:
                raise ValueError

        except (
            TypeError,
            ValueError
        ):

            profile = connection.execute("""
                SELECT *
                FROM farm_profile
                WHERE id = 1
            """).fetchone()

            connection.close()

            return render_template(
                "my_farm.html",
                profile=profile,
                error=
                    "Please enter a valid farm area."
            )

        # -------------------------------------------------
        # Preserve GPS/weather data while updating profile
        # -------------------------------------------------

        connection.execute("""
            INSERT OR IGNORE INTO farm_profile (
                id
            )
            VALUES (1)
        """)

        connection.execute("""
            UPDATE farm_profile

            SET
                farmer_name = ?,
                farm_name = ?,
                area = ?,
                village = ?,
                district = ?,
                state = ?,
                soil_type = ?,
                irrigation_type = ?,
                water_availability = ?,
                current_crop = ?,
                sowing_date = ?,
                updated_at = CURRENT_TIMESTAMP

            WHERE id = 1
        """, (
            farmer_name,
            farm_name,
            area,
            village,
            district,
            state,
            soil_type,
            irrigation_type,
            water_availability,
            current_crop,
            sowing_date
        ))

        connection.commit()

    profile = connection.execute("""
        SELECT *
        FROM farm_profile
        WHERE id = 1
    """).fetchone()

    connection.close()

    return render_template(
        "my_farm.html",
        profile=profile
    )


# =========================================================
# GENERATE ADVISORY
# =========================================================

@app.route(
    "/advisory",
    methods=["POST"]
)
def advisory():

    try:

        nitrogen = float(
            request.form.get(
                "nitrogen",
                0
            )
        )

        phosphorus = float(
            request.form.get(
                "phosphorus",
                0
            )
        )

        potassium = float(
            request.form.get(
                "potassium",
                0
            )
        )

        temperature = float(
            request.form.get(
                "temperature",
                0
            )
        )

        humidity = float(
            request.form.get(
                "humidity",
                0
            )
        )

        ph = float(
            request.form.get(
                "ph",
                7
            )
        )

        rainfall = float(
            request.form.get(
                "rainfall",
                0
            )
        )

    except (
        TypeError,
        ValueError
    ):

        return render_template(
            "advisor.html",
            error=
                "Please enter valid numerical values."
        )

    input_data = {

        "N": nitrogen,
        "P": phosphorus,
        "K": potassium,

        "temperature": temperature,
        "humidity": humidity,

        "ph": ph,
        "rainfall": rainfall
    }

    # -----------------------------------------------------
    # ML PREDICTION
    # -----------------------------------------------------

    predictions = predict_crops(
        input_data
    )

    if not predictions:

        return render_template(
            "advisor.html",
            error=(
                "Unable to generate a crop "
                "prediction. Please train "
                "the model first."
            )
        )

    # -----------------------------------------------------
    # TOP PREDICTION
    # -----------------------------------------------------

    top_prediction = predictions[0]

    crop = top_prediction["crop"]
    confidence = top_prediction["confidence"]

    # -----------------------------------------------------
    # ADVISORY ENGINE
    # -----------------------------------------------------

    advisory_data = generate_advisory(

        crop=crop,

        nitrogen=nitrogen,
        phosphorus=phosphorus,
        potassium=potassium,

        temperature=temperature,
        humidity=humidity,

        ph=ph,
        rainfall=rainfall
    )

    # -----------------------------------------------------
    # SAVE RESULT
    # -----------------------------------------------------

    connection = get_db()

    connection.execute("""
        INSERT INTO advisory_history (

            created_at,

            nitrogen,
            phosphorus,
            potassium,

            temperature,
            humidity,
            ph,
            rainfall,

            recommended_crop,
            confidence,

            irrigation,
            fertilizer,
            soil_advice,
            general_advice
        )

        VALUES (
            ?, ?, ?, ?,
            ?, ?, ?, ?,
            ?, ?,
            ?, ?, ?, ?
        )
    """, (

        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        nitrogen,
        phosphorus,
        potassium,

        temperature,
        humidity,
        ph,
        rainfall,

        crop,
        confidence,

        advisory_data["irrigation"],
        advisory_data["fertilizer"],
        advisory_data["soil_advice"],
        advisory_data["general_advice"]
    ))

    connection.commit()
    connection.close()

    # -----------------------------------------------------
    # RESULT
    # -----------------------------------------------------

    return render_template(

        "result.html",

        predictions=predictions,

        crop=crop,
        confidence=confidence,

        nitrogen=nitrogen,
        phosphorus=phosphorus,
        potassium=potassium,

        temperature=temperature,
        humidity=humidity,

        ph=ph,
        rainfall=rainfall,

        advisory=advisory_data
    )


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
def history():

    connection = get_db()

    records = connection.execute("""
        SELECT *
        FROM advisory_history
        ORDER BY id DESC
        LIMIT 50
    """).fetchall()

    connection.close()

    return render_template(
        "history.html",
        records=records
    )


# =========================================================
# DELETE HISTORY
# =========================================================

@app.route(
    "/history/delete",
    methods=["POST"]
)
def delete_history():

    connection = get_db()

    connection.execute(
        "DELETE FROM advisory_history"
    )

    connection.commit()
    connection.close()

    return redirect(
        url_for("history")
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/api/health")
def health():

    return jsonify({
        "status": "ok",
        "application": "SmartFarm Advisor"
    })


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            5000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
