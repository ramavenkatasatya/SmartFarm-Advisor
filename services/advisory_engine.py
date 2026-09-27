def generate_advisory(
    crop,
    nitrogen,
    phosphorus,
    potassium,
    temperature,
    humidity,
    ph,
    rainfall
):

    # -----------------------------------------------------
    # IRRIGATION
    # -----------------------------------------------------

    if rainfall >= 150:

        irrigation = (
            "Rainfall is relatively high. Avoid unnecessary irrigation "
            "and monitor the field for waterlogging."
        )

    elif rainfall >= 75:

        irrigation = (
            "Moderate rainfall is expected. Irrigate only when the topsoil "
            "starts becoming dry."
        )

    else:

        irrigation = (
            "Rainfall is relatively low. Regular irrigation may be required. "
            "Check soil moisture before watering."
        )


    # -----------------------------------------------------
    # NITROGEN
    # -----------------------------------------------------

    if nitrogen < 40:

        nitrogen_advice = (
            "Nitrogen level appears low. Consider adding an appropriate "
            "nitrogen source based on soil-test recommendations."
        )

    elif nitrogen > 120:

        nitrogen_advice = (
            "Nitrogen level is relatively high. Avoid excessive nitrogen "
            "application because it can increase vegetative growth and "
            "nutrient losses."
        )

    else:

        nitrogen_advice = (
            "Nitrogen level is within a reasonable range for the advisory."
        )


    # -----------------------------------------------------
    # PHOSPHORUS
    # -----------------------------------------------------

    if phosphorus < 30:

        phosphorus_advice = (
            "Phosphorus appears low. Consider a suitable phosphorus source "
            "after confirming soil requirements."
        )

    else:

        phosphorus_advice = (
            "Phosphorus level appears adequate for the current advisory."
        )


    # -----------------------------------------------------
    # POTASSIUM
    # -----------------------------------------------------

    if potassium < 30:

        potassium_advice = (
            "Potassium appears low. Consider potassium supplementation "
            "according to soil-test recommendations."
        )

    else:

        potassium_advice = (
            "Potassium level appears adequate."
        )


    # -----------------------------------------------------
    # SOIL pH
    # -----------------------------------------------------

    if ph < 5.5:

        soil_advice = (
            "The soil is strongly acidic. Consider soil-test-based liming "
            "and consult a local agricultural expert before application."
        )

    elif ph < 6.0:

        soil_advice = (
            "The soil is moderately acidic. Monitor pH and consider "
            "soil-test-based amendments."
        )

    elif ph <= 7.5:

        soil_advice = (
            "Soil pH is in a generally suitable range for many crops."
        )

    elif ph <= 8.0:

        soil_advice = (
            "The soil is mildly alkaline. Monitor nutrient availability "
            "and maintain organic matter."
        )

    else:

        soil_advice = (
            "The soil is strongly alkaline. Soil testing and expert guidance "
            "are recommended before major amendments."
        )


    # -----------------------------------------------------
    # TEMPERATURE
    # -----------------------------------------------------

    if temperature < 15:

        temperature_advice = (
            "Temperature is relatively low. Monitor crop growth and avoid "
            "stress from excessive irrigation."
        )

    elif temperature > 35:

        temperature_advice = (
            "Temperature is relatively high. Monitor heat stress and maintain "
            "adequate soil moisture."
        )

    else:

        temperature_advice = (
            "Temperature is within a moderate range."
        )


    # -----------------------------------------------------
    # HUMIDITY
    # -----------------------------------------------------

    if humidity > 80:

        humidity_advice = (
            "High humidity can increase the risk of fungal problems. "
            "Maintain field ventilation and regularly inspect plants."
        )

    elif humidity < 35:

        humidity_advice = (
            "Low humidity can increase crop water demand. Monitor soil moisture."
        )

    else:

        humidity_advice = (
            "Humidity is within a moderate range."
        )


    # -----------------------------------------------------
    # GENERAL ADVISORY
    # -----------------------------------------------------

    general_advice = (
        f"Based on the supplied soil and environmental conditions, "
        f"{crop} is the highest-ranked crop recommendation from the ML model. "
        f"Use the recommendation as decision support rather than as a "
        f"replacement for local agricultural or soil-test advice."
    )


    return {

        "irrigation": irrigation,

        "fertilizer": (
            f"{nitrogen_advice} "
            f"{phosphorus_advice} "
            f"{potassium_advice}"
        ),

        "soil_advice": (
            f"{soil_advice} "
            f"{temperature_advice} "
            f"{humidity_advice}"
        ),

        "general_advice": general_advice
    }