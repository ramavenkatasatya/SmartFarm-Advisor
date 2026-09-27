def calculate_crop_score(
    temperature,
    humidity,
    ph,
    rainfall,
    soil_type,
    season,
    crop
):
    score = 0
    reasons = []

    # Soil suitability
    suitable_soils = {
        "Rice": ["clay", "loamy"],
        "Maize": ["loamy", "sandy"],
        "Groundnut": ["sandy", "loamy"],
        "Millets": ["sandy", "loamy"],
        "Vegetables": ["loamy"]
    }

    if soil_type in suitable_soils[crop]:
        score += 25
        reasons.append(
            f"{soil_type.capitalize()} soil is suitable for {crop}."
        )
    else:
        reasons.append(
            f"{soil_type.capitalize()} soil is less suitable for {crop}."
        )

    # Season suitability
    suitable_seasons = {
        "Rice": ["kharif"],
        "Maize": ["kharif", "rabi"],
        "Groundnut": ["kharif", "rabi"],
        "Millets": ["kharif", "summer"],
        "Vegetables": ["rabi", "summer"]
    }

    if season in suitable_seasons[crop]:
        score += 20
        reasons.append(
            f"{season.capitalize()} season is suitable."
        )
    else:
        reasons.append(
            f"{season.capitalize()} season may be less suitable."
        )

    # Temperature suitability
    temperature_ranges = {
        "Rice": (20, 35),
        "Maize": (18, 32),
        "Groundnut": (20, 35),
        "Millets": (20, 38),
        "Vegetables": (15, 30)
    }

    min_temp, max_temp = temperature_ranges[crop]

    if min_temp <= temperature <= max_temp:
        score += 20
        reasons.append(
            "Temperature is within the preferred range."
        )
    else:
        reasons.append(
            "Temperature is outside the preferred range."
        )

    # Soil pH suitability
    ph_ranges = {
        "Rice": (5.5, 7.0),
        "Maize": (5.5, 7.5),
        "Groundnut": (6.0, 7.5),
        "Millets": (5.5, 8.0),
        "Vegetables": (5.5, 7.5)
    }

    min_ph, max_ph = ph_ranges[crop]

    if min_ph <= ph <= max_ph:
        score += 15
        reasons.append(
            "Soil pH is within the suitable range."
        )
    else:
        reasons.append(
            "Soil pH may need management."
        )

    # Rainfall suitability
    rainfall_ranges = {
        "Rice": (100, 300),
        "Maize": (50, 200),
        "Groundnut": (50, 150),
        "Millets": (30, 150),
        "Vegetables": (30, 150)
    }

    min_rainfall, max_rainfall = rainfall_ranges[crop]

    if min_rainfall <= rainfall <= max_rainfall:
        score += 10
        reasons.append(
            "Rainfall level is suitable."
        )
    else:
        reasons.append(
            "Rainfall conditions may require irrigation or water management."
        )

    # Humidity suitability
    if 40 <= humidity <= 90:
        score += 10
        reasons.append(
            "Humidity is within an acceptable range."
        )
    else:
        reasons.append(
            "Humidity may create stress or disease risk."
        )

    return {
        "crop": crop,
        "score": score,
        "reasons": reasons
    }


def get_recommendations(
    temperature,
    humidity,
    ph,
    rainfall,
    soil_type,
    season
):
    crops = [
        "Rice",
        "Maize",
        "Groundnut",
        "Millets",
        "Vegetables"
    ]

    results = []

    for crop in crops:

        result = calculate_crop_score(
            temperature,
            humidity,
            ph,
            rainfall,
            soil_type,
            season,
            crop
        )

        results.append(result)

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results