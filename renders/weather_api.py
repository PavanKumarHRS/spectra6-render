import requests


GEOCODING_API_URL = (
    "https://geocoding-api.open-meteo.com/v1/search"
)

WEATHER_API_URL = (
    "https://api.open-meteo.com/v1/forecast"
)

AIR_QUALITY_API_URL = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
)


def get_weather_data(city):

    print("=" * 60)
    print("GETTING WEATHER DATA")
    print(f"CITY = {city}")

    try:

        # ============================================
        # 1. CONVERT CITY -> LATITUDE + LONGITUDE
        # ============================================

        geo_params = {
            "name": city,
            "count": 1,
            "language": "en",
            "format": "json"
        }

        geo_response = requests.get(
            GEOCODING_API_URL,
            params=geo_params,
            timeout=10
        )

        geo_response.raise_for_status()

        geo_json = geo_response.json()

        results = geo_json.get("results")

        if not results:

            print(f"CITY NOT FOUND = {city}")

            return {
                "temperature": None,
                "aqi": None
            }

        location = results[0]

        latitude = location.get("latitude")
        longitude = location.get("longitude")

        city_name = location.get("name")

        print(f"CITY      = {city_name}")
        print(f"LATITUDE  = {latitude}")
        print(f"LONGITUDE = {longitude}")


        # ============================================
        # 2. GET CURRENT TEMPERATURE
        # ============================================

        weather_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m",
            "timezone": "Asia/Kolkata"
        }

        weather_response = requests.get(
            WEATHER_API_URL,
            params=weather_params,
            timeout=10
        )

        weather_response.raise_for_status()

        weather_json = weather_response.json()

        temperature = (
            weather_json
            .get("current", {})
            .get("temperature_2m")
        )

        print(f"TEMPERATURE = {temperature}")


        # ============================================
        # 3. GET CURRENT AQI
        # ============================================

        air_params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "us_aqi",
            "timezone": "Asia/Kolkata"
        }

        air_response = requests.get(
            AIR_QUALITY_API_URL,
            params=air_params,
            timeout=10
        )

        air_response.raise_for_status()

        air_json = air_response.json()

        aqi = (
            air_json
            .get("current", {})
            .get("us_aqi")
        )

        print(f"AQI = {aqi}")

        print("=" * 60)


        # ============================================
        # RETURN DATA
        # ============================================

        return {
            "city": city_name,
            "temperature": temperature,
            "aqi": aqi
        }


    except requests.RequestException as e:

        print(f"WEATHER API ERROR = {e}")

        return {
            "temperature": None,
            "aqi": None
        }


    except Exception as e:

        print(f"WEATHER ERROR = {e}")

        return {
            "temperature": None,
            "aqi": None
        }