import os
import json
import pickle
import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_PATH = os.path.join(
    BASE_DIR,
    "models",
    "crop_model.pkl"
)

METADATA_PATH = os.path.join(
    BASE_DIR,
    "models",
    "model_metadata.json"
)


FEATURES = [
    "N",
    "P",
    "K",
    "temperature",
    "humidity",
    "ph",
    "rainfall"
]


def load_model():
    """Load the trained crop recommendation model."""

    if not os.path.exists(MODEL_PATH):
        print(f"Model not found: {MODEL_PATH}")
        return None

    try:
        with open(MODEL_PATH, "rb") as file:
            return pickle.load(file)

    except Exception as error:
        print(f"Error loading model: {error}")
        return None


def load_metadata():
    """Load model metadata if available."""

    if not os.path.exists(METADATA_PATH):
        return {}

    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as error:
        print(f"Metadata loading error: {error}")
        return {}


def predict_crops(input_data):
    """
    Predict the top 3 crops.

    Expected keys:
    N, P, K, temperature, humidity, ph, rainfall
    """

    model = load_model()

    if model is None:
        return []


    # Use a DataFrame with the SAME feature names
    # used during model training.
    input_df = pd.DataFrame(
        [[
            input_data["N"],
            input_data["P"],
            input_data["K"],
            input_data["temperature"],
            input_data["humidity"],
            input_data["ph"],
            input_data["rainfall"]
        ]],
        columns=FEATURES
    )


    try:

        probabilities = model.predict_proba(input_df)[0]

        classes = model.classes_

    except Exception as error:

        print(f"Probability prediction error: {error}")

        try:

            prediction = model.predict(input_df)[0]

            return [{
                "crop": str(prediction).title(),
                "confidence": 100.0
            }]

        except Exception as prediction_error:

            print(
                f"Prediction error: {prediction_error}"
            )

            return []


    results = []

    for crop, probability in zip(
        classes,
        probabilities
    ):

        results.append({
            "crop": str(crop).title(),
            "confidence": round(
                float(probability) * 100,
                2
            )
        })


    results.sort(
        key=lambda item: item["confidence"],
        reverse=True
    )


    return results[:3]