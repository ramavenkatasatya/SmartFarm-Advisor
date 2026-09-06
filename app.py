import os
import sqlite3
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, jsonify

from services.ml_prediction import predict_crops
from services.advisory_engine import generate_advisory


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DATABASE_PATH = os.path.join(DATABASE_DIR, "smartfarm.db")

os.makedirs(DATABASE_DIR, exist_ok=True)


app = Flask(__name__)


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def get_db():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():

    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS advisory_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,

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

    connection.commit()
    connection.close()


initialize_database()


# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------------------------------------
# CROP ADVISOR
# ---------------------------------------------------------

@app.route("/advisor")
def advisor():
    return render_template("advisor.html")

# ---------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------

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

    connection.close()

    return render_template(
        "dashboard.html",
        latest=latest,
        total_advisories=total_advisories
    )
# ---------------------------------------------------------
# GENERATE ADVISORY
# ---------------------------------------------------------

@app.route("/advisory", methods=["POST"])
def advisory():

    try:

        nitrogen = float(request.form.get("nitrogen", 0))
        phosphorus = float(request.form.get("phosphorus", 0))
        potassium = float(request.form.get("potassium", 0))

        temperature = float(request.form.get("temperature", 0))
        humidity = float(request.form.get("humidity", 0))
        ph = float(request.form.get("ph", 7))
        rainfall = float(request.form.get("rainfall", 0))

    except (TypeError, ValueError):

        return render_template(
            "advisor.html",
            error="Please enter valid numerical values."
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

    predictions = predict_crops(input_data)


    if not predictions:

        return render_template(
            "advisor.html",
            error="Unable to generate a crop prediction. Please train the model first."
        )


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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),

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


# ---------------------------------------------------------
# HISTORY
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# DELETE HISTORY
# ---------------------------------------------------------

@app.route("/history/delete", methods=["POST"])
def delete_history():

    connection = get_db()

    connection.execute("DELETE FROM advisory_history")

    connection.commit()
    connection.close()

    return redirect(url_for("history"))


# ---------------------------------------------------------
# API HEALTH CHECK
# ---------------------------------------------------------

@app.route("/api/health")
def health():

    return jsonify({
        "status": "ok",
        "application": "SmartFarm Advisor"
    })


# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------

if __name__ == "__main__":

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=True
    )
