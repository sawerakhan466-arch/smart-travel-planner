# Smart Travel Planner

A Streamlit travel-planning app with:
- Destination search using Open-Meteo Geocoding
- 7-day weather forecast using Open-Meteo
- Nearby tourism features from OpenStreetMap Overpass API
- Currency conversion using ExchangeRate-API (optional API key)
- Interactive map using Folium

## Deploy on Streamlit Community Cloud

1. Upload `app.py`, `requirements.txt`, `.gitignore`, and this README to a GitHub repository.
2. Do not upload `.streamlit/secrets.toml`.
3. In Streamlit Community Cloud, create an app and select this repository and `app.py`.
4. Open the app's Advanced settings / Secrets section and add:

```toml
EXCHANGE_RATE_API_KEY = "paste_your_key_here"
```

5. Save and deploy.

If you do not configure a currency API key, the destination, weather, attractions, and map features can still work. Currency conversion will show a configuration message.

## Local secrets file (optional)

For local use only, create `.streamlit/secrets.toml` and add the same TOML line. This file is ignored by Git.
