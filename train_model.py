import os
import json
import pickle

import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_PATH = os.path.join(
    BASE_DIR,
    "data",
    "crop_recommendation.csv"
)

MODEL_DIR = os.path.join(
    BASE_DIR,
    "models"
)

MODEL_PATH = os.path.join(
    MODEL_DIR,
    "crop_model.pkl"
)

METADATA_PATH = os.path.join(
    MODEL_DIR,
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

TARGET = "label"


def main():

    print("\n===================================")
    print(" SMARTFARM MODEL TRAINING")
    print("===================================\n")


    if not os.path.exists(DATA_PATH):

        raise FileNotFoundError(
            f"Dataset not found: {DATA_PATH}"
        )


    df = pd.read_csv(DATA_PATH)


    if df.empty:

        raise ValueError(
            "The dataset is empty. Add training data to "
            "data/crop_recommendation.csv before training."
        )


    required_columns = FEATURES + [TARGET]

    missing = [
        column
        for column in required_columns
        if column not in df.columns
    ]


    if missing:

        raise ValueError(
            f"Missing columns: {missing}\n"
            f"Required columns: {required_columns}"
        )


    df = df.dropna(
        subset=required_columns
    )


    X = df[FEATURES]

    y = df[TARGET]


    print("Dataset shape:", df.shape)

    print("Number of crops:", y.nunique())

    print("\nCrop distribution:")

    print(y.value_counts())


    X_train, X_test, y_train, y_test = train_test_split(

        X,
        y,

        test_size=0.20,

        random_state=42,

        stratify=y
    )


    model = RandomForestClassifier(

        n_estimators=300,

        random_state=42,

        class_weight="balanced",

        n_jobs=-1
    )


    print("\nTraining Random Forest...")

    model.fit(
        X_train,
        y_train
    )


    predictions = model.predict(
        X_test
    )


    accuracy = accuracy_score(
        y_test,
        predictions
    )


    macro_f1 = f1_score(
        y_test,
        predictions,
        average="macro"
    )


    weighted_f1 = f1_score(
        y_test,
        predictions,
        average="weighted"
    )


    print("\n===================================")
    print(" MODEL PERFORMANCE")
    print("===================================")

    print(
        f"Accuracy     : {accuracy:.4f}"
    )

    print(
        f"Macro F1     : {macro_f1:.4f}"
    )

    print(
        f"Weighted F1  : {weighted_f1:.4f}"
    )


    print("\nClassification Report:\n")

    print(
        classification_report(
            y_test,
            predictions
        )
    )


    os.makedirs(
        MODEL_DIR,
        exist_ok=True
    )


    with open(
        MODEL_PATH,
        "wb"
    ) as file:

        pickle.dump(
            model,
            file
        )


    metadata = {

        "model": "RandomForestClassifier",

        "features": FEATURES,

        "target": TARGET,

        "n_estimators": 300,

        "random_state": 42,

        "dataset_rows": int(len(df)),

        "number_of_classes": int(y.nunique()),

        "accuracy": round(
            float(accuracy),
            4
        ),

        "macro_f1": round(
            float(macro_f1),
            4
        ),

        "weighted_f1": round(
            float(weighted_f1),
            4
        ),

        "feature_importance": {
            feature: round(
                float(importance),
                6
            )

            for feature, importance

            in zip(
                FEATURES,
                model.feature_importances_
            )
        }

    }


    with open(
        METADATA_PATH,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4
        )


    print("\nModel saved:")
    print(MODEL_PATH)

    print("\nMetadata saved:")
    print(METADATA_PATH)

    print("\nTraining completed successfully.")


if __name__ == "__main__":
    main()