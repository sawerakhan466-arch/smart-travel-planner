import requests
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Smart Travel Planner",
    page_icon="✈️",
    layout="wide"
)

st.title("✈️ Smart Travel Planner")
st.write("Plan your trip with destination weather, nearby attractions, and currency conversion.")

st.sidebar.header("Trip Settings")
city = st.sidebar.text_input("Destination city", value="Chitral")
base_currency = st.sidebar.selectbox(
    "Your currency", ["PKR", "USD", "EUR", "GBP", "AED", "SAR"], index=0
)
target_currency = st.sidebar.selectbox(
    "Currency to convert into", ["USD", "PKR", "EUR", "GBP", "AED", "SAR"], index=1
)
amount = st.sidebar.number_input("Amount", min_value=0.0, value=1000.0, step=100.0)

HEADERS = {
    "User-Agent": "SmartTravelPlanner/1.0 (educational project)"
}


def get_destination(city_name):
    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": city_name,
        "count": 1,
        "language": "en",
        "format": "json"
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    results = response.json().get("results", [])
    return results[0] if results else None


def get_weather(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": 7
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def weather_description(code):
    descriptions = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with heavy hail"
    }
    return descriptions.get(code, "Weather conditions vary")


def get_attractions(latitude, longitude):
    # Search for selected tourism-related OpenStreetMap features within 5 km.
    query = f"""
    [out:json][timeout:25];
    (
      node(around:5000,{latitude},{longitude})[tourism~"attraction|museum|viewpoint|zoo|gallery"];
      way(around:5000,{latitude},{longitude})[tourism~"attraction|museum|viewpoint|zoo|gallery"];
      relation(around:5000,{latitude},{longitude})[tourism~"attraction|museum|viewpoint|zoo|gallery"];
    );
    out center tags;
    """
    url = "https://overpass-api.de/api/interpreter"
    response = requests.post(url, data=query, headers=HEADERS, timeout=40)
    response.raise_for_status()
    elements = response.json().get("elements", [])

    places = []
    for item in elements:
        tags = item.get("tags", {})
        name = tags.get("name")
        if not name:
            continue

        if "lat" in item and "lon" in item:
            lat, lon = item["lat"], item["lon"]
        elif "center" in item:
            lat, lon = item["center"]["lat"], item["center"]["lon"]
        else:
            continue

        places.append({
            "name": name,
            "type": tags.get("tourism", "Place"),
            "latitude": lat,
            "longitude": lon
        })

    # Avoid showing duplicate names.
    unique_places = {}
    for place in places:
        unique_places[place["name"]] = place
    return list(unique_places.values())[:30]


def get_currency_rate(base, target):
    # Read the key from Streamlit Cloud Secrets or local environment.
    try:
        api_key = st.secrets.get("EXCHANGE_RATE_API_KEY", "")
    except Exception:
        api_key = ""

    if not api_key:
        return None, "ExchangeRate-API key is not configured in Streamlit Secrets."

    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}"
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    data = response.json()

    if data.get("result") != "success":
        error_type = data.get("error-type", "Unknown API error")
        return None, f"Currency API returned: {error_type}"

    rate = data.get("conversion_rates", {}).get(target)
    if rate is None:
        return None, f"Exchange rate for {target} was not returned."

    return rate, None


if st.sidebar.button("Plan My Trip", type="primary", use_container_width=True):
    if not city.strip():
        st.warning("Please enter a destination city.")
    else:
        with st.spinner(f"Finding travel information for {city}..."):
            try:
                destination = get_destination(city.strip())

                if not destination:
                    st.error("Destination not found. Please try another city name.")
                    st.stop()

                latitude = destination["latitude"]
                longitude = destination["longitude"]
                st.session_state["destination"] = destination
                st.session_state["weather"] = get_weather(latitude, longitude)

                try:
                    st.session_state["attractions"] = get_attractions(latitude, longitude)
                    st.session_state["attraction_error"] = None
                except requests.exceptions.RequestException as exc:
                    st.session_state["attractions"] = []
                    st.session_state["attraction_error"] = str(exc)

                st.session_state["trip_loaded"] = True

            except requests.exceptions.RequestException as exc:
                st.error(f"Could not retrieve destination information: {exc}")
                st.session_state["trip_loaded"] = False
            except (KeyError, ValueError) as exc:
                st.error(f"The API returned unexpected data: {exc}")
                st.session_state["trip_loaded"] = False


if st.session_state.get("trip_loaded"):
    destination = st.session_state["destination"]
    weather = st.session_state["weather"]
    attractions = st.session_state.get("attractions", [])

    place_name = destination.get("name", city)
    country = destination.get("country", "")
    st.subheader(f"Your destination: {place_name}, {country}")
    st.caption(
        f"Coordinates: {destination['latitude']:.4f}, {destination['longitude']:.4f}"
    )

    daily = weather.get("daily", {})
    if daily:
        st.subheader("🌤️ 7-Day Weather Forecast")
        weather_rows = []
        for i, date in enumerate(daily.get("time", [])):
            code = daily.get("weather_code", [None] * len(daily.get("time", [])))[i]
            weather_rows.append({
                "Date": date,
                "Weather": weather_description(code),
                "Max °C": daily.get("temperature_2m_max", [None] * len(daily.get("time", [])))[i],
                "Min °C": daily.get("temperature_2m_min", [None] * len(daily.get("time", [])))[i],
                "Rain chance %": daily.get("precipitation_probability_max", [None] * len(daily.get("time", [])))[i]
            })
        st.dataframe(pd.DataFrame(weather_rows), use_container_width=True, hide_index=True)

    st.subheader("💱 Currency Converter")
    if st.button("Convert Amount"):
        try:
            rate, error = get_currency_rate(base_currency, target_currency)
            if error:
                st.warning(error)
            else:
                converted = amount * rate
                st.success(
                    f"{amount:,.2f} {base_currency} = {converted:,.2f} {target_currency}"
                )
                st.caption(f"Rate: 1 {base_currency} = {rate} {target_currency}")
        except requests.exceptions.RequestException as exc:
            st.error(f"Could not connect to the currency service: {exc}")

    st.subheader("📍 Nearby Tourist Attractions")
    if st.session_state.get("attraction_error"):
        st.warning("Attraction search is temporarily unavailable. Please try again later.")
    elif attractions:
        st.dataframe(pd.DataFrame(attractions)[["name", "type"]], use_container_width=True, hide_index=True)
    else:
        st.info("No named attractions were found in the nearby OpenStreetMap data.")

    st.subheader("🗺️ Destination Map")
    map_view = folium.Map(
        location=[destination["latitude"], destination["longitude"]],
        zoom_start=12
    )
    folium.Marker(
        [destination["latitude"], destination["longitude"]],
        tooltip=place_name,
        popup=f"{place_name}, {country}",
        icon=folium.Icon(color="red", icon="info-sign")
    ).add_to(map_view)

    for place in attractions:
        folium.Marker(
            [place["latitude"], place["longitude"]],
            tooltip=place["name"],
            popup=f"{place['name']} ({place['type']})",
            icon=folium.Icon(color="blue", icon="camera")
        ).add_to(map_view)

    st_folium(map_view, width=None, height=500, use_container_width=True)

    st.caption(
        "Weather data: Open-Meteo. Map and attraction data: OpenStreetMap contributors. "
        "Check local conditions and official travel advice before travelling."
    )
else:
    st.info("Enter a destination in the sidebar and select **Plan My Trip** to begin.")
