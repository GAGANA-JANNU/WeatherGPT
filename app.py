import os
import math
import html
import textwrap
import requests
import streamlit as st
import streamlit.components.v1 as components
from datetime import datetime, timezone
from dotenv import load_dotenv

# ============================================================
# CONFIG
# ============================================================

st.set_page_config(
    page_title="WeatherGPT | Intelligent Weather Platform",
    page_icon="🌦️",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()


# Streamlit Markdown treats deeply-indented HTML as a code block.
# The app contains many Python-indented HTML templates, so clean only
# unsafe HTML blocks before sending them to Streamlit.
_original_st_markdown = st.markdown

def _clean_markdown(body, *args, **kwargs):
    if kwargs.get("unsafe_allow_html") and isinstance(body, str):
        # Streamlit's Markdown parser can turn indented HTML containing
        # blank lines into a literal code block. Normalize the complete
        # HTML payload before Streamlit sees it.
        body = textwrap.dedent(body)
        lines = body.splitlines()
        # Remove empty lines only when the payload contains HTML tags.
        # This preserves ordinary markdown while making nested HTML blocks
        # render reliably regardless of Python indentation.
        if any("<div" in line or "</div>" in line or "<span" in line or "</span>" in line for line in lines):
            body = "\n".join(line.rstrip() for line in lines if line.strip())
        else:
            body = body.strip("\n")
    return _original_st_markdown(body, *args, **kwargs)

st.markdown = _clean_markdown


# ============================================================
# API KEY
# Supports common OpenWeather variable names without changing
# the user's existing .env file.
# ============================================================

API_KEY = (
    os.getenv("OPENWEATHER_API_KEY")
    or os.getenv("OPENWEATHERMAP_API_KEY")
    or os.getenv("WEATHER_API_KEY")
    or os.getenv("API_KEY")
)


# ============================================================
# SESSION STATE
# ============================================================

defaults = {
    "page": "Dashboard",
    "location": "Bengaluru",
    "weather": None,
    "forecast": None,
    "lat": None,
    "lon": None,
    "location_name": "Bengaluru",
    "country": "India",
    "mode": "Student",
    "language": "English",
    "last_question": "",
    "chat_history": [],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# COLORS / CSS
# ============================================================

st.markdown(
    """
<style>

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background:
        radial-gradient(circle at 80% 5%, rgba(91, 91, 255, 0.22), transparent 28%),
        radial-gradient(circle at 45% 40%, rgba(0, 190, 255, 0.12), transparent 25%),
        linear-gradient(135deg, #06111f 0%, #0a1730 45%, #151342 100%);
    color: #f8fafc;
}

/* Hide Streamlit decoration */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {background: transparent !important;}

/* Sidebar */
section[data-testid="stSidebar"] {
    background:
        radial-gradient(circle at 20% 15%, rgba(74, 144, 226, 0.13), transparent 25%),
        linear-gradient(180deg, #06111f 0%, #081525 100%);
    border-right: 1px solid rgba(255,255,255,0.08);
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.2rem;
}

/* Sidebar buttons */
section[data-testid="stSidebar"] .stButton > button {
    width: 100%;
    border: 1px solid transparent;
    background: transparent;
    color: #9fb0c7;
    text-align: left;
    border-radius: 12px;
    padding: 0.65rem 0.8rem;
    font-weight: 600;
    transition: all 0.2s ease;
}

section[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(88, 166, 255, 0.10);
    color: white;
    border-color: rgba(88,166,255,0.18);
}

/* Inputs */
.stTextInput input,
.stSelectbox div[data-baseweb="select"] > div {
    background: rgba(255,255,255,0.95) !important;
    color: #162033 !important;
    border-radius: 12px !important;
    border: 1px solid rgba(255,255,255,0.30) !important;
}

.stTextInput label,
.stSelectbox label {
    color: #c9d6e8 !important;
}

/* Buttons */
.stButton > button {
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.12);
    background: linear-gradient(135deg, #2678ff, #7357ff);
    color: white;
    font-weight: 700;
    min-height: 42px;
    transition: all 0.2s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 25px rgba(66, 111, 255, 0.28);
}

/* Cards */
.weather-card {
    background:
        linear-gradient(145deg, rgba(255,255,255,0.095), rgba(255,255,255,0.035));
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 20px;
    padding: 20px;
    box-shadow: 0 15px 40px rgba(0,0,0,0.20);
    backdrop-filter: blur(15px);
}

.metric-card {
    background: rgba(255,255,255,0.055);
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 16px;
    padding: 17px;
    min-height: 105px;
}

.metric-icon {
    font-size: 25px;
}

.metric-value {
    font-size: 24px;
    font-weight: 800;
    color: white;
    margin-top: 5px;
}

.metric-label {
    color: #9fb1c9;
    font-size: 13px;
}

.hero {
    position: relative;
    overflow: hidden;
    background:
        radial-gradient(circle at 90% 15%, rgba(89, 170, 255, 0.28), transparent 25%),
        radial-gradient(circle at 10% 90%, rgba(132, 88, 255, 0.20), transparent 25%),
        linear-gradient(135deg, #123b5a, #182d68 50%, #2b225c);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 25px;
    padding: 32px;
    margin: 10px 0 22px 0;
}

.hero-small-label {
    color: #76d4ff;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
}

.hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: clamp(34px, 4vw, 58px);
    line-height: 1.03;
    font-weight: 800;
    margin: 12px 0;
    color: white;
}

.gradient-text {
    background: linear-gradient(90deg, #48c7ff, #9276ff, #dc7cff);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.hero-description {
    max-width: 760px;
    color: #c5d3e8;
    font-size: 16px;
    line-height: 1.7;
}

.live-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(20, 220, 135, 0.08);
    border: 1px solid rgba(20, 220, 135, 0.18);
    padding: 9px 14px;
    border-radius: 999px;
    color: #9af0c5;
    font-weight: 700;
    font-size: 13px;
}

.green-dot {
    width: 9px;
    height: 9px;
    background: #21e39b;
    border-radius: 50%;
    box-shadow: 0 0 12px #21e39b;
}

.section-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 23px;
    font-weight: 800;
    margin: 22px 0 12px 0;
}

.section-subtitle {
    color: #8fa4bd;
    font-size: 14px;
    margin-bottom: 15px;
}

.action-card {
    background: linear-gradient(
        135deg,
        rgba(0, 180, 255, 0.14),
        rgba(113, 83, 255, 0.13)
    );
    border: 1px solid rgba(103, 185, 255, 0.18);
    border-radius: 18px;
    padding: 20px;
}

.alert-card {
    border-radius: 18px;
    padding: 19px;
    background: linear-gradient(
        135deg,
        rgba(255, 175, 50, 0.15),
        rgba(255, 77, 77, 0.08)
    );
    border: 1px solid rgba(255,180,70,0.22);
}

.safe-card {
    border-radius: 18px;
    padding: 19px;
    background: rgba(30, 220, 150, 0.08);
    border: 1px solid rgba(30, 220, 150, 0.18);
}

.forecast-card {
    background: rgba(255,255,255,0.055);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 15px 10px;
    text-align: center;
}

.big-temp {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 64px;
    font-weight: 800;
    line-height: 1;
}

.location-name {
    font-size: 27px;
    font-weight: 800;
}

.muted {
    color: #93a6bf;
}

.chat-user {
    background: linear-gradient(135deg, #2d70e8, #6954db);
    border-radius: 16px 16px 3px 16px;
    padding: 14px 17px;
    margin: 8px 0 8px 20%;
}

.chat-ai {
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px 16px 16px 3px;
    padding: 14px 17px;
    margin: 8px 20% 8px 0;
}

.mode-card {
    background: linear-gradient(135deg, rgba(124,92,255,0.14), rgba(54,179,255,0.09));
    border: 1px solid rgba(140,130,255,0.17);
    border-radius: 18px;
    padding: 18px;
}

.footer-note {
    color: #70839b;
    font-size: 12px;
    text-align: center;
    margin-top: 35px;
    padding: 20px;
}

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# WEATHER FUNCTIONS
# ============================================================

@st.cache_data(ttl=300)
def geocode_location(location):
    """Convert city/town/location into coordinates."""
    if not API_KEY:
        return None

    url = "https://api.openweathermap.org/geo/1.0/direct"

    params = {
        "q": location,
        "limit": 1,
        "appid": API_KEY,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            return None

        item = data[0]

        return {
            "lat": item["lat"],
            "lon": item["lon"],
            "name": item.get("name", location),
            "state": item.get("state", ""),
            "country": item.get("country", ""),
        }

    except Exception:
        return None


@st.cache_data(ttl=300)
def get_current_weather(lat, lon):
    """Get live current weather."""
    if not API_KEY:
        return None

    url = "https://api.openweathermap.org/data/2.5/weather"

    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    except Exception:
        return None


@st.cache_data(ttl=300)
def get_forecast(lat, lon):
    """Get 5-day / 3-hour forecast."""
    if not API_KEY:
        return None

    url = "https://api.openweathermap.org/data/2.5/forecast"

    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY,
        "units": "metric",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()

    except Exception:
        return None


def load_location(location):
    """Load a new location and all live data."""
    if not API_KEY:
        st.error(
            "⚠️ Weather API key not found. "
            "Please check your existing .env file."
        )
        return False

    with st.spinner(f"🌍 Finding live weather for {location}..."):

        geo = geocode_location(location)

        if not geo:
            st.error(
                f"❌ Could not find **{location}**. "
                "Try a city, town, district or location such as "
                "`Bengaluru`, `Bhadravathi`, `Mysuru`, `Mumbai`."
            )
            return False

        weather = get_current_weather(geo["lat"], geo["lon"])
        forecast = get_forecast(geo["lat"], geo["lon"])

        if not weather:
            st.error("❌ Live weather data could not be retrieved.")
            return False

        st.session_state.location = location
        st.session_state.location_name = geo["name"]
        st.session_state.country = geo["country"]
        st.session_state.lat = geo["lat"]
        st.session_state.lon = geo["lon"]
        st.session_state.weather = weather
        st.session_state.forecast = forecast

    return True


# ============================================================
# WEATHER HELPERS
# ============================================================

def weather_icon(main):
    icons = {
        "Clear": "☀️",
        "Clouds": "☁️",
        "Rain": "🌧️",
        "Drizzle": "🌦️",
        "Thunderstorm": "⛈️",
        "Snow": "❄️",
        "Mist": "🌫️",
        "Fog": "🌫️",
        "Haze": "🌫️",
        "Smoke": "💨",
        "Dust": "🌪️",
        "Sand": "🌪️",
        "Ash": "🌋",
        "Squall": "💨",
        "Tornado": "🌪️",
    }

    return icons.get(main, "🌤️")


def rain_probability():
    """Estimate rain probability from forecast."""
    forecast = st.session_state.forecast

    if not forecast or "list" not in forecast:
        return 0

    values = []

    for item in forecast["list"][:8]:
        pop = item.get("pop", 0)
        values.append(pop * 100)

    return round(max(values)) if values else 0


def current_risk():
    weather = st.session_state.weather

    if not weather:
        return "Unknown", "No live data available.", "⚪"

    rain = rain_probability()
    wind = weather.get("wind", {}).get("speed", 0)
    temp = weather.get("main", {}).get("temp", 25)

    if rain >= 70 or wind >= 15:
        return (
            "High",
            "Weather conditions may affect outdoor plans.",
            "🔴",
        )

    if rain >= 40 or wind >= 10 or temp >= 38:
        return (
            "Moderate",
            "Some weather precautions are recommended.",
            "🟠",
        )

    return (
        "Low",
        "Current conditions look relatively comfortable.",
        "🟢",
    )


def recommendation():
    weather = st.session_state.weather

    if not weather:
        return "Search for a location to get a live recommendation."

    mode = st.session_state.mode
    rain = rain_probability()

    temp = weather.get("main", {}).get("temp", 25)
    wind = weather.get("wind", {}).get("speed", 0)
    condition = weather.get("weather", [{}])[0].get("main", "")

    if rain >= 70:
        base = "🌧️ Rain is likely. Carry an umbrella and keep some travel buffer."

    elif rain >= 40:
        base = "🌦️ There is a meaningful chance of rain. An umbrella is advisable."

    elif temp >= 36:
        base = "☀️ It is quite warm. Prefer shade, hydration and lighter outdoor activity."

    elif wind >= 10:
        base = "💨 Winds are noticeable. Be careful with outdoor activities and two-wheelers."

    else:
        base = "🌤️ Conditions look suitable for normal outdoor plans."

    mode_advice = {
        "Student": " 🎓 For students: check your commute and keep study/travel plans flexible.",
        "Farmer": " 🌾 For farmers: monitor rainfall and wind before irrigation or field activity.",
        "Commuter": " 🚗 For commuters: allow extra travel time if rain or wind increases.",
        "Event / Outdoor": " 🎉 For outdoor events: keep a covered backup option available.",
    }

    return base + mode_advice.get(mode, "")


def best_time_to_go():
    forecast = st.session_state.forecast

    if not forecast:
        return "Search for a location first."

    candidates = []

    for item in forecast.get("list", [])[:12]:
        pop = item.get("pop", 0)
        wind = item.get("wind", {}).get("speed", 0)
        temp = item.get("main", {}).get("temp", 25)

        score = pop * 100 + wind

        if 20 <= temp <= 34:
            score -= 10

        candidates.append((score, item))

    if not candidates:
        return "No forecast window available."

    candidates.sort(key=lambda x: x[0])

    best = candidates[0][1]

    dt = datetime.fromtimestamp(best["dt"], tz=timezone.utc)

    # Forecast timestamps are UTC; OpenWeather forecast also provides
    # timezone offset at city level.
    offset = forecast.get("city", {}).get("timezone", 0)

    local_seconds = best["dt"] + offset

    local_dt = datetime.fromtimestamp(local_seconds, tz=timezone.utc)

    rain = round(best.get("pop", 0) * 100)

    return (
        f"🕐 Around **{local_dt.strftime('%I:%M %p')}** looks like "
        f"a comparatively better window, with about **{rain}% rain probability**."
    )


# ============================================================
# LANGUAGE
# ============================================================

def txt(en, kn=None):
    """Return Kannada text when Kannada is selected, otherwise English."""
    if st.session_state.language == "Kannada" and kn:
        return kn
    return en


# Common interface translations. Weather values and API data remain live.
UI = {
    "Dashboard": ("ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", "Dashboard"),
    "WeatherGPT AI": ("ವೆದರ್‌GPT AI", "WeatherGPT AI"),
    "Voice Assistant": ("ಧ್ವನಿ ಸಹಾಯಕ", "Voice Assistant"),
    "Smart Planner": ("ಸ್ಮಾರ್ಟ್ ಪ್ಲಾನರ್", "Smart Planner"),
    "Forecast": ("ಮುನ್ನೋಟ", "Forecast"),
    "Smart Alerts": ("ಸ್ಮಾರ್ಟ್ ಎಚ್ಚರಿಕೆಗಳು", "Smart Alerts"),
    "How It Works": ("ಇದು ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ", "How It Works"),
    "Explore": ("ಅನ್ವೇಷಿಸಿ", "Explore"),
    "Personal Mode": ("ವೈಯಕ್ತಿಕ ಮೋಡ್", "Personal Mode"),
    "Language": ("ಭಾಷೆ", "Language"),
    "Choose location": ("ನಿಮ್ಮ ಸ್ಥಳವನ್ನು ಆಯ್ಕೆಮಾಡಿ", "Choose your location"),
    "Search": ("ಹುಡುಕಿ", "Search"),
    "Refresh": ("ರಿಫ್ರೆಶ್", "Refresh"),
    "Live Weather": ("ಲೈವ್ ಹವಾಮಾನ", "Live Weather"),
    "Current Weather Risk": ("ಪ್ರಸ್ತುತ ಹವಾಮಾನ ಅಪಾಯ", "Current Weather Risk"),
    "Recommended Action": ("ಶಿಫಾರಸು ಮಾಡಿದ ಕ್ರಮ", "Recommended Action"),
    "Decision factors": ("ನಿರ್ಧಾರಕ್ಕೆ ಮುಖ್ಯ ಅಂಶಗಳು", "Decision factors"),
    "Hourly Forecast": ("ಗಂಟೆಯ ಹವಾಮಾನ ಮುನ್ನೋಟ", "Hourly Forecast Timeline"),
    "7-Day Outlook": ("7 ದಿನಗಳ ಮುನ್ನೋಟ", "7-Day Outlook"),
    "Voice Weather Assistant": ("ಧ್ವನಿ ಹವಾಮಾನ ಸಹಾಯಕ", "Voice Weather Assistant"),
}

def ui(key):
    value = UI.get(key, (key, key))
    return value[0] if st.session_state.language == "Kannada" else value[1]


# Page/section copy used by the visible interface.  The weather values
# themselves remain live API data.
COPY = {
    "dashboard_hero_label": ("ಬುದ್ಧಿವಂತ ಹವಾಮಾನ ವೇದಿಕೆ", "INTELLIGENT WEATHER PLATFORM"),
    "dashboard_hero_1": ("ಹವಾಮಾನ ದತ್ತಾಂಶ ಉಪಯುಕ್ತ.", "Weather data is useful."),
    "dashboard_hero_2": ("ಹವಾಮಾನ ನಿರ್ಧಾರಗಳು ಇನ್ನಷ್ಟು ಉತ್ತಮ.", "Weather decisions are better."),
    "dashboard_desc": (
        "WeatherGPT ಲೈವ್ ಹವಾಮಾನ ಮಾಹಿತಿ, ಸಂವಾದಾತ್ಮಕ AI, ಸ್ಥಳ ಬುದ್ಧಿಮತ್ತೆ ಮತ್ತು "
        "ವಿದ್ಯಾರ್ಥಿಗಳು, ರೈತರು, ಪ್ರಯಾಣಿಕರು ಹಾಗೂ ಹೊರಾಂಗಣ ಯೋಜನೆಗಳಿಗೆ ವೈಯಕ್ತಿಕ ಸಲಹೆಗಳನ್ನು ಒಟ್ಟುಗೂಡಿಸುತ್ತದೆ.",
        "WeatherGPT combines live weather information, conversational AI, location intelligence "
        "and personalized action recommendations for students, farmers, commuters and outdoor planners.",
    ),
    "live_weather": ("🌦️ ಲೈವ್ ಹವಾಮಾನ", "🌦️ Live Weather Now"),
    "what_do": ("🎯 ಈಗ ಏನು ಮಾಡಬೇಕು?", "🎯 What should I do now?"),
    "rain_decision": ("🌧️ ಮಳೆ ಮತ್ತು ಛತ್ರಿ ನಿರ್ಧಾರ", "🌧️ Rain & Umbrella Decision"),
    "best_time": ("🕐 ಹೋಗಲು ಉತ್ತಮ ಸಮಯ", "🕐 Best time to go"),
    "personal_mode": ("👤 ವೈಯಕ್ತಿಕ ಹವಾಮಾನ ಮೋಡ್", "👤 Personalized Weather Mode"),
    "ai_label": ("ಸಂವಾದಾತ್ಮಕ ಹವಾಮಾನ ಬುದ್ಧಿಮತ್ತೆ", "CONVERSATIONAL WEATHER INTELLIGENCE"),
    "ai_title1": ("WeatherGPT ಗೆ ಕೇಳಿ.", "Ask WeatherGPT."),
    "ai_title2": ("ಸಂಖ್ಯೆ ಮಾತ್ರವಲ್ಲ — ಕ್ರಮ ಪಡೆಯಿರಿ.", "Get an action, not just a number."),
    "ai_desc": (
        "ಮಳೆ, ಪ್ರಯಾಣ, ಹೊರಾಂಗಣ ಯೋಜನೆಗಳು, ತಾಪಮಾನ ಮತ್ತು ಹವಾಮಾನ ಪರಿಸ್ಥಿತಿಗಳ ಬಗ್ಗೆ "
        "ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಸಹಜ ಭಾಷೆಯಲ್ಲಿ ಪ್ರಶ್ನೆ ಕೇಳಿ.",
        "Ask natural-language questions in English or Kannada about rain, travel, outdoor plans, "
        "temperature and weather conditions.",
    ),
    "planner_label": ("ವೈಯಕ್ತಿಕ ಹವಾಮಾನ ಯೋಜನೆ", "PERSONALIZED WEATHER PLANNING"),
    "planner_title1": ("ಚುರುಕಾಗಿ ಯೋಜಿಸಿ.", "Plan smarter."),
    "planner_title2": ("ಹವಾಮಾನವನ್ನು ಕ್ರಮವಾಗಿ ಪರಿವರ್ತಿಸಿ.", "Weather becomes an action."),
    "forecast_label": ("ಹವಾಮಾನ ಮುನ್ನೋಟ", "WEATHER OUTLOOK"),
    "forecast_title": ("ಮುಂದೇನು ಬರುತ್ತಿದೆ ನೋಡಿ.", "See what's coming."),
    "forecast_desc": (
        "ಲೈವ್ ಮುನ್ನೋಟ ದತ್ತಾಂಶದಿಂದ ಗಂಟೆಯ ಪ್ರವೃತ್ತಿಗಳು ಮತ್ತು ಬಹು-ದಿನ ಯೋಜನೆ ಮಾಹಿತಿಯನ್ನು ನೋಡಿ.",
        "Hourly weather trends and multi-day planning information powered by live forecast data.",
    ),
    "alerts_label": ("ಸಕ್ರಿಯ ಹವಾಮಾನ ಅಪಾಯ", "PROACTIVE WEATHER RISK"),
    "alerts_title1": ("ಹೋಗುವ ಮೊದಲು", "Know the risk"),
    "alerts_title2": ("ಅಪಾಯ ತಿಳಿದುಕೊಳ್ಳಿ.", "before you go."),
    "alerts_desc": (
        "WeatherGPT ಕಚ್ಚಾ ಹವಾಮಾನ ಸೂಚನೆಗಳನ್ನು ಅರ್ಥವಾಗುವ ಅಪಾಯ ಮಟ್ಟ ಮತ್ತು ಪ್ರಾಯೋಗಿಕ ಮುನ್ನೆಚ್ಚರಿಕೆಗಳಾಗಿ ಪರಿವರ್ತಿಸುತ್ತದೆ.",
        "WeatherGPT converts raw weather signals into understandable risk information and practical precautions.",
    ),
    "how_label": ("ನಿರ್ಣಾಯಕರಿಗಾಗಿ • ವ್ಯವಸ್ಥೆಯ ವಿವರಣೆ", "FOR JUDGES • SYSTEM EXPLANATION"),
    "how_title1": ("ಹವಾಮಾನ ದತ್ತಾಂಶದಿಂದ", "From weather data"),
    "how_title2": ("ಉಪಯುಕ್ತ ನಿರ್ಧಾರಗಳವರೆಗೆ.", "to useful decisions."),
}

def cp(key):
    pair = COPY.get(key, (key, key))
    return pair[0] if st.session_state.language == "Kannada" else pair[1]


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        """
        <div style="padding:10px 10px 25px 10px;">
            <div style="font-size:58px;">🌦️</div>
            <div style="
                font-family:'Space Grotesk';
                font-size:30px;
                font-weight:800;
                color:white;
            ">
                WeatherGPT
            </div>
            <div style="
                color:#7090b1;
                font-size:11px;
                font-weight:800;
                letter-spacing:2px;
                margin-top:6px;
            ">
                WEATHER INTELLIGENCE PLATFORM
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            color:#6f87a4;
            font-size:12px;
            font-weight:800;
            letter-spacing:2px;
            margin:10px 10px;
        ">
        EXPLORE
        </div>
        """,
        unsafe_allow_html=True,
    )

    pages = [
        ("🏠", "Dashboard"),
        ("🤖", "WeatherGPT AI"),
        ("🎙️", "Voice Assistant"),
        ("🎯", "Smart Planner"),
        ("📅", "Forecast"),
        ("⚠️", "Smart Alerts"),
        ("🧠", "How It Works"),
    ]

    for icon, page in pages:
        display_page = ui(page)
        if st.button(
            f"{icon}  {display_page}",
            key=f"nav_{page}",
            use_container_width=True,
        ):
            st.session_state.page = page
            st.rerun()

    st.markdown("---")

    st.markdown(
        """
        <div style="
            color:#6f87a4;
            font-size:12px;
            font-weight:800;
            letter-spacing:2px;
            margin:10px;
        ">
        PERSONAL MODE
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("ಇದಕ್ಕಾಗಿ ಯೋಜನೆ" if st.session_state.language == "Kannada" else "Planning for")

    mode_options = {
        "Student": "🎓 Student",
        "Farmer": "🌾 Farmer",
        "Commuter": "🚗 Commuter",
        "Event / Outdoor": "🎉 Event / Outdoor",
    }
    mode_labels = list(mode_options.values())
    current_mode_label = mode_options.get(st.session_state.mode, "🎓 Student")
    selected_mode_label = st.selectbox(
        "Planning mode",
        mode_labels,
        index=mode_labels.index(current_mode_label),
        key="personal_mode_selector",
        label_visibility="collapsed",
    )
    new_mode = next(
        mode for mode, label in mode_options.items()
        if label == selected_mode_label
    )
    st.session_state.mode = new_mode

    st.markdown(
        """
        <div style="
            color:#6f87a4;
            font-size:12px;
            font-weight:800;
            letter-spacing:2px;
            margin:18px 10px 8px;
        ">
        LANGUAGE
        </div>
        """,
        unsafe_allow_html=True,
    )

    language_options = {
        "English": "🇬🇧 English",
        "Kannada": "🇮🇳 ಕನ್ನಡ (Kannada)",
    }
    language_labels = list(language_options.values())
    current_language_label = language_options.get(st.session_state.language, "🇬🇧 English")
    selected_language_label = st.selectbox(
        "🌐 Language",
        language_labels,
        index=language_labels.index(current_language_label),
        key="language_selector",
        label_visibility="visible",
    )
    new_language = next(
        language for language, label in language_options.items()
        if label == selected_language_label
    )
    if new_language != st.session_state.language:
        st.session_state.language = new_language
        st.rerun()

    st.markdown(
        f"""
        <div style="
            margin-top:12px;
            padding:11px 13px;
            border-radius:12px;
            background:rgba(39,120,255,0.10);
            border:1px solid rgba(100,160,255,0.15);
            color:#b9d4ff;
            font-size:12px;
            line-height:1.5;
        ">
            🌐 <b>Language:</b> {"ಕನ್ನಡ" if st.session_state.language == "Kannada" else "English"}<br>
            <span style="color:#8098b5;">
                {"ನೀವು ಭಾಷೆ ಬದಲಿಸಿದಾಗ ಬೆಂಬಲಿತ ಇಂಟರ್ಫೇಸ್ ಲೇಬಲ್‌ಗಳು ಬದಲಾಗುತ್ತವೆ." if st.session_state.language == "Kannada" else "Supported interface labels update when you change this setting."}
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            margin-top:25px;
            padding:15px;
            border-radius:16px;
            background:rgba(255,255,255,0.04);
            border:1px solid rgba(255,255,255,0.07);
        ">
            <div style="font-size:13px;color:#9db1ca;">
                🇮🇳 India-focused
            </div>
            <div style="font-size:12px;color:#6f849d;margin-top:5px;">
                Live weather intelligence
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# TOP STATUS BAR
# ============================================================

st.markdown(
    """
    <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        padding:12px 18px;
        margin-bottom:22px;
        border-radius:16px;
        background:rgba(255,255,255,0.035);
        border:1px solid rgba(255,255,255,0.07);
    ">
        <div class="live-pill">
            <span class="green-dot"></span>
            LIVE WEATHER INTELLIGENCE
        </div>
        <div style="color:#8095ae;font-size:13px;">
            🇮🇳 India-focused • Real-time API data
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# LOCATION SEARCH
# ============================================================

location_title = (
    "ನಿಮ್ಮ ಸ್ಥಳವನ್ನು ಆಯ್ಕೆಮಾಡಿ"
    if st.session_state.language == "Kannada"
    else "Choose your location"
)
location_help = (
    "ನಗರ, ಪಟ್ಟಣ, ಜಿಲ್ಲೆ ಅಥವಾ ಸ್ಥಳದ ಹೆಸರನ್ನು ನಮೂದಿಸಿ — ನಂತರ ಹುಡುಕಿ ಒತ್ತಿರಿ."
    if st.session_state.language == "Kannada"
    else "Enter a city, town, district or location name — then press Search."
)

st.markdown(
    f"""
    <div style="font-size:25px;font-weight:800;margin-bottom:4px;">
        📍 {location_title}
    </div>
    <div style="color:#8399b2;font-size:14px;margin-bottom:12px;">
        {location_help}
    </div>
    """,
    unsafe_allow_html=True,
)

search_col, btn_col, refresh_col = st.columns([5, 1.15, 1.15])

with search_col:
    location_input = st.text_input(
        "Location",
        value=st.session_state.location,
        placeholder="Example: Bengaluru, Bhadravathi, Mysuru, Mumbai...",
        label_visibility="collapsed",
    )

with btn_col:
    search_clicked = st.button(
        f"🔎 {ui('Search')}",
        use_container_width=True,
    )

with refresh_col:
    refresh_clicked = st.button(
        f"🔄 {ui('Refresh')}",
        use_container_width=True,
    )


if search_clicked:

    if location_input.strip():
        if load_location(location_input.strip()):
            st.success(
                f"📍 Live weather loaded for "
                f"**{st.session_state.location_name}**"
            )
            st.rerun()

if refresh_clicked:

    if st.session_state.lat and st.session_state.lon:

        with st.spinner("🔄 Refreshing live weather..."):

            weather = get_current_weather(
                st.session_state.lat,
                st.session_state.lon,
            )

            forecast = get_forecast(
                st.session_state.lat,
                st.session_state.lon,
            )

            if weather:
                st.session_state.weather = weather

            if forecast:
                st.session_state.forecast = forecast

        st.rerun()

    else:
        load_location(st.session_state.location)


# ============================================================
# FIRST LOAD
# ============================================================

if st.session_state.weather is None:

    if not load_location(st.session_state.location):
        st.warning(
            "⚠️ Enter a location above and press Search to load live weather."
        )
        st.stop()


weather = st.session_state.weather
forecast = st.session_state.forecast


# ============================================================
# WEATHER DATA
# ============================================================

main_weather = weather.get("weather", [{}])[0]

condition = main_weather.get("main", "Unknown")
description = main_weather.get("description", "No description").title()
icon = weather_icon(condition)

temp = weather.get("main", {}).get("temp", 0)
feels = weather.get("main", {}).get("feels_like", 0)
humidity = weather.get("main", {}).get("humidity", 0)
pressure = weather.get("main", {}).get("pressure", 0)
visibility = weather.get("visibility", 0) / 1000
wind = weather.get("wind", {}).get("speed", 0)

rain = rain_probability()

risk, risk_description, risk_icon = current_risk()


# ============================================================
# DASHBOARD
# ============================================================

# The selected page is rendered directly below. This small status
# card makes navigation state obvious during a live hackathon demo.
mode_display = {
    "Student": "🎓 Student",
    "Farmer": "🌾 Farmer",
    "Commuter": "🚗 Commuter",
    "Event / Outdoor": "🎉 Event / Outdoor",
}.get(st.session_state.mode, st.session_state.mode)

st.markdown(
    f"""
    <div style="
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:12px;
        padding:10px 16px;
        margin-bottom:14px;
        border-radius:13px;
        background:rgba(255,255,255,.035);
        border:1px solid rgba(255,255,255,.07);
    ">
        <div style="font-weight:800;">{ui(st.session_state.page)}</div>
        <div style="color:#91a6bf;font-size:12px;">
            {"🇮🇳 ಕನ್ನಡ" if st.session_state.language == "Kannada" else "🇬🇧 English"}
            &nbsp;•&nbsp;
            {mode_display}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.page == "Dashboard":

    st.markdown(
        f"""
        <div class="hero">

            <div class="hero-small-label">
                🌐 {cp("dashboard_hero_label")}
            </div>

            <div class="hero-title">
                {cp("dashboard_hero_1")}<br>
                <span class="gradient-text">
                    {cp("dashboard_hero_2")}
                </span>
            </div>

            <div class="hero-description">
                {cp("dashboard_desc")}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # Current weather
    st.markdown(
        f'<div class="section-title">{cp("live_weather")}</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns([1.25, 1])

    with left:

        st.markdown(
            f"""
            <div class="weather-card">

                <div class="location-name">
                    📍 {st.session_state.location_name}
                </div>

                <div class="muted" style="margin-top:5px;">
                    {st.session_state.country} • Live conditions
                </div>

                <div style="
                    display:flex;
                    align-items:center;
                    gap:22px;
                    margin-top:25px;
                ">

                    <div style="font-size:75px;">
                        {icon}
                    </div>

                    <div>
                        <div class="big-temp">
                            {round(temp)}°C
                        </div>

                        <div style="
                            color:#b8c8dc;
                            font-size:16px;
                            margin-top:6px;
                        ">
                            {description}
                        </div>

                        <div style="
                            color:#8297b0;
                            margin-top:6px;
                        ">
                            Feels like {round(feels)}°C
                        </div>
                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    with right:

        m1, m2 = st.columns(2)

        with m1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon">💧</div>
                    <div class="metric-value">{humidity}%</div>
                    <div class="metric-label">Humidity</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with m2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon">💨</div>
                    <div class="metric-value">{wind:.1f}</div>
                    <div class="metric-label">Wind m/s</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.write("")

        m3, m4 = st.columns(2)

        with m3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon">🌡️</div>
                    <div class="metric-value">{pressure}</div>
                    <div class="metric-label">Pressure hPa</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with m4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-icon">👁️</div>
                    <div class="metric-value">{visibility:.1f}</div>
                    <div class="metric-label">Visibility km</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ========================================================
    # WHAT SHOULD I DO
    # ========================================================

    st.markdown(
        f'<div class="section-title">{cp("what_do")}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="action-card">

            <div style="
                font-size:24px;
                font-weight:800;
                color:white;
            ">
                {recommendation()}
            </div>

            <div style="
                margin-top:13px;
                color:#8fa7c0;
            ">
                Personalized for <b>{st.session_state.mode}</b>
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # RAIN DECISION
    # ========================================================

    st.markdown(
        f'<div class="section-title">{cp("rain_decision")}</div>',
        unsafe_allow_html=True,
    )

    if rain >= 70:

        st.markdown(
            f"""
            <div class="alert-card">
                <div style="font-size:23px;font-weight:800;">
                    ☔ Take an umbrella
                </div>
                <div style="color:#c9d6e7;margin-top:8px;">
                    Rain probability in the near forecast window:
                    <b>{rain}%</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    elif rain >= 40:

        st.markdown(
            f"""
            <div class="alert-card">
                <div style="font-size:23px;font-weight:800;">
                    🌦️ Umbrella recommended
                </div>
                <div style="color:#c9d6e7;margin-top:8px;">
                    There is a meaningful chance of rain:
                    <b>{rain}%</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            f"""
            <div class="safe-card">
                <div style="font-size:23px;font-weight:800;">
                    🌤️ Umbrella probably not needed
                </div>
                <div style="color:#b9d4ca;margin-top:8px;">
                    Current forecast rain probability:
                    <b>{rain}%</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ========================================================
    # BEST TIME
    # ========================================================

    st.markdown(
        f'<div class="section-title">{cp("best_time")}</div>',
        unsafe_allow_html=True,
    )

    st.info(best_time_to_go())

    # ========================================================
    # MODE
    # ========================================================

    st.markdown(
        f'<div class="section-title">{cp("personal_mode")}</div>',
        unsafe_allow_html=True,
    )

    mode_messages = {
        "Student": (
            "🎓 Student Mode",
            "Plan classes, commuting and outdoor activities around rain and heat."
        ),
        "Farmer": (
            "🌾 Farmer Mode",
            "Use rainfall, wind and temperature information when planning field activities."
        ),
        "Commuter": (
            "🚗 Commuter Mode",
            "Use weather risk and rainfall information to plan safer, more comfortable travel."
        ),
        "Event / Outdoor": (
            "🎉 Event Planning Mode",
            "Check rain, wind and temperature before outdoor events and keep a backup plan."
        ),
    }

    title, message = mode_messages[st.session_state.mode]

    st.markdown(
        f"""
        <div class="mode-card">
            <div style="font-size:21px;font-weight:800;">
                {title}
            </div>
            <div style="color:#9db1ca;margin-top:8px;">
                {message}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# WEATHERGPT AI
# ============================================================

elif st.session_state.page == "WeatherGPT AI":

    st.markdown(
        f"""
        <div class="hero">

            <div class="hero-small-label">
                🤖 {cp("ai_label")}
            </div>

            <div class="hero-title">
                {cp("ai_title1")}<br>
                <span class="gradient-text">
                    {cp("ai_title2")}
                </span>
            </div>

            <div class="hero-description">
                {cp("ai_desc")}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        "### 💬 Natural-language Weather Assistant"
    )

    question = st.text_input(
        "Ask a weather question",
        placeholder=(
            "Example: Will it rain today? "
            "Should I carry an umbrella? "
            "ಇಂದು ಮಳೆ ಬರುತ್ತದೆಯೇ?"
        ),
    )

    examples = [
        "🌧️ Will it rain today?",
        "☔ Do I need an umbrella?",
        "🚗 Is it a good time to travel?",
        "🌡️ Is the weather hot?",
        "🎓 Is it okay to go to college?",
        "🌾 Is today's weather suitable for farming?",
    ]

    cols = st.columns(3)

    for i, example in enumerate(examples):

        with cols[i % 3]:

            if st.button(
                example,
                key=f"example_{i}",
                use_container_width=True,
            ):
                question = example

    if question:

        q = question.lower()

        if any(
            word in q
            for word in [
                "rain",
                "umbrella",
                "ಮಳೆ",
                "rainy",
            ]
        ):

            if rain >= 70:
                answer = (
                    f"☔ Yes, rain risk is significant. "
                    f"The near forecast reaches about {rain}%. "
                    "Carry an umbrella."
                )

            elif rain >= 40:
                answer = (
                    f"🌦️ There is a moderate rain possibility "
                    f"of about {rain}%. An umbrella is advisable."
                )

            else:
                answer = (
                    f"🌤️ The current forecast indicates a relatively "
                    f"low rain probability of about {rain}%."
                )

        elif any(
            word in q
            for word in [
                "travel",
                "go",
                "commute",
                "college",
                "office",
                "ಹೊರಗೆ",
                "ಪ್ರಯಾಣ",
            ]
        ):

            answer = (
                f"{recommendation()} "
                f"{best_time_to_go()}"
            )

        elif any(
            word in q
            for word in [
                "temperature",
                "hot",
                "cold",
                "ಬಿಸಿ",
                "ತಂಪು",
            ]
        ):

            answer = (
                f"🌡️ It is currently around "
                f"**{round(temp)}°C**, with a feels-like "
                f"temperature of **{round(feels)}°C**."
            )

        elif any(
            word in q
            for word in [
                "farmer",
                "farming",
                "crop",
                "agriculture",
                "ರೈತ",
                "ಕೃಷಿ",
            ]
        ):

            answer = (
                f"🌾 For farming decisions, the current temperature "
                f"is {round(temp)}°C, humidity is {humidity}% and "
                f"near-term rain probability is about {rain}%. "
                "Use these as planning signals and verify local field "
                "conditions before taking action."
            )

        else:

            answer = (
                f"🌦️ In {st.session_state.location_name}, "
                f"the current condition is **{description}** at "
                f"around **{round(temp)}°C**. "
                f"Rain probability is approximately **{rain}%**. "
                f"{recommendation()}"
            )

        st.session_state.chat_history.append(
            ("user", question)
        )

        st.session_state.chat_history.append(
            ("assistant", answer)
        )

    for role, message in st.session_state.chat_history[-10:]:

        if role == "user":

            st.markdown(
                f"""
                <div class="chat-user">
                    🧑 {message}
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                f"""
                <div class="chat-ai">
                    🤖 {message}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ========================================================
    # VOICE ASSISTANT
    # ========================================================

    st.markdown(
        '<div class="section-title">🎙️ Voice Weather Assistant</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="action-card">

        <div style="font-size:22px;font-weight:800;">
            🗣️ Speak your weather question
        </div>

        <div style="color:#91a6bf;margin-top:7px;line-height:1.6;">
            Use your browser's microphone to ask a question.
            Voice recognition support depends on your browser.
        </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # Browser voice UI
    st.components.v1.html(
        """
        <!DOCTYPE html>
        <html>
        <head>
        <style>
        body {
            background: transparent;
            font-family: Arial, sans-serif;
            color: white;
            margin: 0;
        }

        button {
            border: none;
            padding: 13px 20px;
            border-radius: 12px;
            background: linear-gradient(135deg,#2878ff,#7658ff);
            color: white;
            font-size: 15px;
            font-weight: bold;
            cursor: pointer;
        }

        #status {
            margin-top: 12px;
            color: #9db1ca;
            font-size: 14px;
        }

        #result {
            margin-top: 12px;
            padding: 12px;
            border-radius: 10px;
            background: rgba(255,255,255,.07);
            min-height: 22px;
        }
        </style>
        </head>

        <body>

        <button onclick="startVoice()">
            🎙️ Start Speaking
        </button>

        <div id="status">
            Click the button and speak.
        </div>

        <div id="result"></div>

        <script>

        function startVoice() {

            const SpeechRecognition =
                window.SpeechRecognition ||
                window.webkitSpeechRecognition;

            if (!SpeechRecognition) {

                document.getElementById("status").innerText =
                    "⚠️ Voice recognition is not supported by this browser. Try Chrome or Edge.";

                return;
            }

            const recognition = new SpeechRecognition();

            recognition.lang = "en-IN";
            recognition.interimResults = false;
            recognition.maxAlternatives = 1;

            recognition.onstart = function() {
                document.getElementById("status").innerText =
                    "🎙️ Listening... Speak now.";
            };

            recognition.onresult = function(event) {

                const text =
                    event.results[0][0].transcript;

                document.getElementById("result").innerText =
                    "You said: " + text;

                document.getElementById("status").innerText =
                    "✅ Voice captured. Type the same question in the WeatherGPT box above to get the live answer.";

                // Browser speech output
                const speech =
                    new SpeechSynthesisUtterance(
                        "I heard: " + text
                    );

                speech.lang = "en-IN";

                window.speechSynthesis.speak(speech);
            };

            recognition.onerror = function(event) {

                document.getElementById("status").innerText =
                    "⚠️ Microphone error: " + event.error;
            };

            recognition.onend = function() {

                if (
                    document.getElementById("status").innerText
                    === "🎙️ Listening... Speak now."
                ) {
                    document.getElementById("status").innerText =
                        "Listening stopped.";
                }
            };

            recognition.start();
        }

        </script>

        </body>
        </html>
        """,
        height=180,
    )

    st.info(
        "💡 For the hackathon demo: open WeatherGPT in Chrome/Edge, "
        "allow microphone access, click **Start Speaking**, and ask your question."
    )


# ============================================================
# VOICE ASSISTANT
# ============================================================

elif st.session_state.page == "Voice Assistant":

    st.markdown(
        """
        <div class="hero">
            <div class="hero-small-label">🎙️ HANDS-FREE WEATHER INTELLIGENCE</div>
            <div class="hero-title">
                Talk to WeatherGPT.<br>
                <span class="gradient-text">Ask. Understand. Act.</span>
            </div>
            <div class="hero-description">
                Speak naturally in English or ಕನ್ನಡ. The assistant uses the
                currently selected location and live weather signals to give
                practical, weather-aware guidance.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="action-card" style="text-align:center;padding:28px;">
            <div style="font-size:54px;">🎙️</div>
            <div style="font-size:25px;font-weight:800;margin-top:8px;">
                Voice Weather Assistant
            </div>
            <div style="color:#9db1ca;margin-top:8px;">
                📍 {st.session_state.location_name}, {st.session_state.country}
                &nbsp; • &nbsp; {st.session_state.mode} mode
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    voice_language = "kn-IN" if st.session_state.language == "Kannada" else "en-IN"
    voice_lang_label = "ಕನ್ನಡ" if st.session_state.language == "Kannada" else "English"

    voice_payload = {
        "location": st.session_state.location_name,
        "country": st.session_state.country,
        "temp": round(float(temp)),
        "feels": round(float(feels)),
        "humidity": int(humidity),
        "wind": round(float(wind), 1),
        "rain": int(rain),
        "condition": description,
        "mode": st.session_state.mode,
        "language": voice_lang_label,
    }
    import json as _json
    payload_json = _json.dumps(voice_payload).replace("</", "<\\/")

    components.html(
        f"""
        <!doctype html>
        <html>
        <head>
        <meta charset="utf-8">
        <style>
          * {{ box-sizing:border-box; }}
          body {{
            margin:0;
            font-family:Inter,Arial,sans-serif;
            background:transparent;
            color:#fff;
          }}
          .wrap {{
            padding:4px 2px 8px;
          }}
          .panel {{
            border:1px solid rgba(255,255,255,.10);
            border-radius:24px;
            padding:26px;
            background:linear-gradient(135deg,rgba(39,120,255,.16),rgba(128,78,255,.13));
            box-shadow:0 18px 50px rgba(0,0,0,.18);
          }}
          .mic {{
            width:82px;height:82px;border-radius:50%;
            margin:0 auto 14px;
            display:flex;align-items:center;justify-content:center;
            font-size:38px;
            background:linear-gradient(135deg,#2878ff,#8a5cff);
            box-shadow:0 10px 30px rgba(70,100,255,.35);
          }}
          .mic.listening {{
            animation:pulse 1.15s infinite;
          }}
          @keyframes pulse {{
            0% {{ box-shadow:0 0 0 0 rgba(70,100,255,.55); }}
            70% {{ box-shadow:0 0 0 22px rgba(70,100,255,0); }}
            100% {{ box-shadow:0 0 0 0 rgba(70,100,255,0); }}
          }}
          .title {{ text-align:center;font-size:24px;font-weight:800; }}
          .sub {{ text-align:center;color:#9db1ca;margin-top:7px;line-height:1.5; }}
          .actions {{ display:flex;gap:10px;justify-content:center;margin-top:20px;flex-wrap:wrap; }}
          button {{
            border:0;border-radius:13px;padding:13px 20px;
            font-size:15px;font-weight:800;color:#fff;cursor:pointer;
          }}
          #start {{ background:linear-gradient(135deg,#2878ff,#7658ff); }}
          #stop {{ background:rgba(255,255,255,.09);border:1px solid rgba(255,255,255,.12); }}
          button:disabled {{ opacity:.45;cursor:not-allowed; }}
          .status {{
            margin-top:16px;text-align:center;color:#8fa5bf;font-size:14px;
            min-height:22px;
          }}
          .box {{
            margin-top:16px;padding:17px;border-radius:16px;
            background:rgba(255,255,255,.055);
            border:1px solid rgba(255,255,255,.07);
          }}
          .label {{
            font-size:11px;font-weight:800;letter-spacing:1.5px;color:#7892ad;
          }}
          .text {{ margin-top:7px;font-size:17px;line-height:1.6; }}
          .answer {{
            margin-top:16px;padding:18px;border-radius:17px;
            background:linear-gradient(135deg,rgba(34,197,94,.10),rgba(39,120,255,.10));
            border:1px solid rgba(255,255,255,.08);
          }}
          .tips {{
            display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:18px;
          }}
          .tip {{
            padding:8px 11px;border-radius:999px;
            background:rgba(255,255,255,.06);
            color:#b8c7d8;font-size:12px;
          }}
          .error {{ color:#ffb4b4; }}
        </style>
        </head>
        <body>
        <div class="wrap">
          <div class="panel">
            <div id="mic" class="mic">🎙️</div>
            <div class="title">Press and speak</div>
            <div class="sub">Language: {html.escape(voice_lang_label)} · Browser microphone required</div>

            <div class="actions">
              <button id="start">🎙️ Start Speaking</button>
              <button id="stop" disabled>⏹ Stop</button>
            </div>

            <div id="status" class="status">Ready. Try: “Will it rain today?”</div>

            <div class="box">
              <div class="label">🗣️ YOUR QUESTION</div>
              <div id="question" class="text">Your spoken question will appear here.</div>
            </div>

            <div id="answerBox" class="answer" style="display:none;">
              <div class="label">🤖 WEATHERGPT RESPONSE</div>
              <div id="answer" class="text"></div>
            </div>

            <div class="tips">
              <span class="tip">🌧️ Will it rain today?</span>
              <span class="tip">☂️ Do I need an umbrella?</span>
              <span class="tip">🎓 Can I go to college?</span>
              <span class="tip">🌾 Is it good for farming?</span>
              <span class="tip">🌡️ Is it hot?</span>
            </div>
          </div>
        </div>

        <script>
        const DATA = {payload_json};
        const LANG = "{voice_language}";
        const startBtn = document.getElementById("start");
        const stopBtn = document.getElementById("stop");
        const statusEl = document.getElementById("status");
        const questionEl = document.getElementById("question");
        const answerBox = document.getElementById("answerBox");
        const answerEl = document.getElementById("answer");
        const mic = document.getElementById("mic");

        let recognition = null;

        function speak(text) {{
          if (!("speechSynthesis" in window)) return;
          window.speechSynthesis.cancel();
          const u = new SpeechSynthesisUtterance(text);
          u.lang = LANG;
          u.rate = 0.95;
          u.pitch = 1;
          window.speechSynthesis.speak(u);
        }}

        function makeAnswer(q) {{
          const x = q.toLowerCase();
          const rain = DATA.rain;
          const temp = DATA.temp;
          const wind = DATA.wind;
          const humidity = DATA.humidity;
          const loc = DATA.location;

          const rainWords = ["rain","umbrella","मಳೆ","ಮಳೆ","barish","baarish"];
          const travelWords = ["travel","go","commute","college","office","outside","ಪ್ರಯಾಣ","ಹೊರಗೆ"];
          const farmWords = ["farm","farmer","farming","crop","agriculture","ರೈತ","ಕೃಷಿ"];
          const tempWords = ["temperature","hot","cold","weather","ಬಿಸಿ","ತಂಪು","ಹವಾಮಾನ"];

          const has = words => words.some(w => x.includes(w));

          if (has(rainWords)) {{
            if (rain >= 70) return `☔ Rain risk is high in ${{loc}} at about ${{rain}}%. Carry an umbrella and keep extra travel time.`;
            if (rain >= 40) return `🌦️ Rain is possible in ${{loc}} with about ${{rain}}% near-term probability. Carrying an umbrella is advisable.`;
            return `🌤️ Rain probability is relatively low at about ${{rain}}% in ${{loc}} right now.`;
          }}

          if (has(farmWords)) {{
            return `🌾 For ${{loc}}, the current temperature is ${{temp}}°C, humidity is ${{humidity}}%, and near-term rain probability is ${{rain}}%. Use these as planning signals and verify local field conditions before important farm decisions.`;
          }}

          if (has(travelWords)) {{
            if (rain >= 70 || wind >= 15) return `🚗 Travel needs extra caution in ${{loc}}. Rain risk is ${{rain}}% and wind is ${{wind}} m/s. Keep a backup plan and allow extra time.`;
            if (rain >= 40 || wind >= 10) return `🚗 Travel is possible, but conditions may change. Rain probability is ${{rain}}% and wind is ${{wind}} m/s. Keep an umbrella and some time buffer.`;
            return `🚗 Current conditions in ${{loc}} look relatively comfortable for normal travel. Temperature is ${{temp}}°C and rain probability is ${{rain}}%.`;
          }}

          if (has(tempWords)) {{
            return `🌡️ In ${{loc}}, it is currently about ${{temp}}°C with a feels-like temperature of ${{DATA.feels}}°C. Conditions: ${{DATA.condition}}.`;
          }}

          return `🌦️ In ${{loc}}, it is currently ${{DATA.condition}} at about ${{temp}}°C. Rain probability is around ${{rain}}%, humidity is ${{humidity}}%, and wind is ${{wind}} m/s.`;
        }}

        function handleTranscript(text) {{
          questionEl.textContent = text;
          const answer = makeAnswer(text);
          answerEl.textContent = answer;
          answerBox.style.display = "block";
          statusEl.textContent = "✅ WeatherGPT generated a live weather-aware response.";
          speak(answer);
        }}

        function startVoice() {{
          const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
          if (!SR) {{
            statusEl.innerHTML = '<span class="error">⚠️ Voice recognition is not supported here. Please use the latest Chrome or Edge.</span>';
            return;
          }}

          recognition = new SR();
          recognition.lang = LANG;
          recognition.interimResults = false;
          recognition.continuous = false;
          recognition.maxAlternatives = 1;

          recognition.onstart = () => {{
            startBtn.disabled = true;
            stopBtn.disabled = false;
            mic.classList.add("listening");
            statusEl.textContent = "🎙️ Listening… speak now.";
          }};

          recognition.onresult = event => {{
            const text = event.results[0][0].transcript;
            handleTranscript(text);
          }};

          recognition.onerror = event => {{
            statusEl.innerHTML = '<span class="error">⚠️ Microphone error: ' + event.error + '. Check browser microphone permission.</span>';
          }};

          recognition.onend = () => {{
            startBtn.disabled = false;
            stopBtn.disabled = true;
            mic.classList.remove("listening");
          }};

          try {{
            recognition.start();
          }} catch(e) {{
            statusEl.textContent = "⚠️ Could not start microphone. Please try again.";
          }}
        }}

        startBtn.onclick = startVoice;
        stopBtn.onclick = () => {{
          if (recognition) recognition.stop();
        }};
        </script>
        </body>
        </html>
        """,
        height=650,
        scrolling=False,
    )

    st.info(
        "🎤 For the live demo, use Chrome/Edge and allow microphone access. "
        "The assistant speaks the response aloud using your browser's speech engine."
    )


# ============================================================
# SMART PLANNER
# ============================================================

elif st.session_state.page == "Smart Planner":

    st.markdown(
        f"""
        <div class="hero">

            <div class="hero-small-label">
                🎯 WEATHER-AWARE DECISION ENGINE
            </div>

            <div class="hero-title">
                {cp("planner_title1")}<br>
                <span class="gradient-text">
                    {cp("planner_title2")}
                </span>
            </div>

            <div class="hero-description">
                Personalized recommendations based on your selected
                activity mode and live weather conditions.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="mode-card">
            <div style="font-size:14px;color:#8198b1;">
                CURRENT MODE
            </div>

            <div style="
                font-size:30px;
                font-weight:800;
                margin-top:5px;
            ">
                {st.session_state.mode}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="section-title">🎯 {ui("Recommended Action")}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="action-card">
            <div style="font-size:22px;font-weight:800;">
                {recommendation()}
            </div>
            <div style="margin-top:14px;color:#8fa5bf;">
                {best_time_to_go()}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="section-title">🧩 {ui("Decision factors")}</div>',
        unsafe_allow_html=True,
    )

    factors = [
        ("🌧️ Rain", f"{rain}%"),
        ("🌡️ Temperature", f"{round(temp)}°C"),
        ("💨 Wind", f"{wind:.1f} m/s"),
        ("💧 Humidity", f"{humidity}%"),
    ]

    cols = st.columns(4)

    for i, (name, value) in enumerate(factors):

        with cols[i]:

            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-label">{name}</div>
                    <div class="metric-value">{value}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# FORECAST
# ============================================================

elif st.session_state.page == "Forecast":

    st.markdown(
        f"""
        <div class="hero">

            <div class="hero-small-label">
                📅 {cp("forecast_label")}
            </div>

            <div class="hero-title">
                {cp("forecast_title")}
            </div>

            <div class="hero-description">
                {cp("forecast_desc")}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # ========================================================
    # HOURLY
    # ========================================================

    st.markdown(
        f'<div class="section-title">⏱️ {ui("Hourly Forecast")}</div>',
        unsafe_allow_html=True,
    )

    if forecast:

        hourly_items = forecast.get("list", [])[:8]

        cols = st.columns(len(hourly_items))

        for i, item in enumerate(hourly_items):

            local_seconds = (
                item["dt"]
                + forecast.get("city", {}).get("timezone", 0)
            )

            dt = datetime.fromtimestamp(
                local_seconds,
                tz=timezone.utc,
            )

            temp_h = item["main"]["temp"]
            pop = round(item.get("pop", 0) * 100)

            condition_h = item.get(
                "weather",
                [{}]
            )[0].get("main", "")

            with cols[i]:

                st.markdown(
                    f"""
                    <div class="forecast-card">

                        <div style="
                            color:#92a7bf;
                            font-size:12px;
                        ">
                            {dt.strftime('%I %p')}
                        </div>

                        <div style="
                            font-size:30px;
                            margin:9px 0;
                        ">
                            {weather_icon(condition_h)}
                        </div>

                        <div style="
                            font-size:20px;
                            font-weight:800;
                        ">
                            {round(temp_h)}°
                        </div>

                        <div style="
                            color:#77cfff;
                            font-size:12px;
                            margin-top:7px;
                        ">
                            🌧️ {pop}%
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # ========================================================
    # 7 DAY / AVAILABLE DAILY
    # ========================================================

    st.markdown(
        f'<div class="section-title">📅 {ui("7-Day Outlook")}</div>',
        unsafe_allow_html=True,
    )

    if forecast:

        daily = {}

        for item in forecast.get("list", []):

            local_seconds = (
                item["dt"]
                + forecast.get("city", {}).get("timezone", 0)
            )

            dt = datetime.fromtimestamp(
                local_seconds,
                tz=timezone.utc,
            )

            date_key = dt.strftime("%Y-%m-%d")

            if date_key not in daily:
                daily[date_key] = []

            daily[date_key].append(item)

        days = list(daily.items())[:7]

        cols = st.columns(len(days))

        for i, (date_key, items) in enumerate(days):

            max_temp = max(
                x["main"]["temp_max"]
                for x in items
            )

            min_temp = min(
                x["main"]["temp_min"]
                for x in items
            )

            rain_day = round(
                max(
                    x.get("pop", 0)
                    for x in items
                ) * 100
            )

            condition_day = items[len(items)//2].get(
                "weather",
                [{}]
            )[0].get("main", "")

            dt = datetime.strptime(
                date_key,
                "%Y-%m-%d"
            )

            with cols[i]:

                st.markdown(
                    f"""
                    <div class="forecast-card">

                        <div style="
                            font-weight:800;
                            color:white;
                        ">
                            {dt.strftime('%a')}
                        </div>

                        <div style="
                            font-size:34px;
                            margin:8px;
                        ">
                            {weather_icon(condition_day)}
                        </div>

                        <div style="
                            font-size:18px;
                            font-weight:800;
                        ">
                            {round(max_temp)}°
                            /
                            {round(min_temp)}°
                        </div>

                        <div style="
                            color:#72cfff;
                            font-size:12px;
                            margin-top:6px;
                        ">
                            🌧️ {rain_day}%
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# ============================================================
# ALERTS
# ============================================================

elif st.session_state.page == "Smart Alerts":

    st.markdown(
        f"""
        <div class="hero">

            <div class="hero-small-label">
                ⚠️ {cp("alerts_label")}
            </div>

            <div class="hero-title">
                {cp("alerts_title1")}<br>
                before you go.
            </div>

            <div class="hero-description">
                {cp("alerts_desc")}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="section-title">🚨 {ui("Current Weather Risk")}</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="alert-card">

            <div style="
                font-size:36px;
                font-weight:800;
            ">
                {risk_icon} {risk} Risk
            </div>

            <div style="
                margin-top:8px;
                color:#bdcde0;
            ">
                {risk_description}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-title">📡 Live Risk Signals</div>',
        unsafe_allow_html=True,
    )

    signals = []

    if rain >= 70:
        signals.append(
            ("🌧️ Heavy rain possibility", "High")
        )
    elif rain >= 40:
        signals.append(
            ("🌦️ Rain possibility", "Moderate")
        )
    else:
        signals.append(
            ("🌤️ Rain possibility", "Low")
        )

    if wind >= 15:
        signals.append(
            ("💨 Strong wind", "High")
        )
    elif wind >= 10:
        signals.append(
            ("💨 Wind", "Moderate")
        )
    else:
        signals.append(
            ("💨 Wind", "Low")
        )

    if temp >= 38:
        signals.append(
            ("☀️ Heat", "High")
        )
    elif temp >= 34:
        signals.append(
            ("🌡️ Heat", "Moderate")
        )
    else:
        signals.append(
            ("🌡️ Heat", "Low")
        )

    cols = st.columns(3)

    for i, (name, level) in enumerate(signals):

        with cols[i]:

            st.markdown(
                f"""
                <div class="metric-card">

                    <div style="
                        font-size:17px;
                        font-weight:700;
                    ">
                        {name}
                    </div>

                    <div style="
                        font-size:25px;
                        font-weight:800;
                        margin-top:10px;
                    ">
                        {level}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        f'<div class="section-title">🎯 {ui("Recommended Action")}</div>',
        unsafe_allow_html=True,
    )

    st.info(recommendation())


# ============================================================
# HOW IT WORKS
# ============================================================

elif st.session_state.page == "How It Works":

    st.markdown(
        f"""
        <div class="hero">

            <div class="hero-small-label">
                🧠 {cp("how_label")}
            </div>

            <div class="hero-title">
                {cp("how_title1")}<br>
                <span class="gradient-text">
                    {cp("how_title2")}
                </span>
            </div>

            <div class="hero-description">
                WeatherGPT is designed as a decision-support layer
                above live weather information.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    steps = [
        (
            "1",
            "📍 Location Intelligence",
            "User enters a city, town or location. The system converts the location into geographic coordinates."
        ),
        (
            "2",
            "🌦️ Live Weather API",
            "Current weather and forecast information are retrieved from the weather service."
        ),
        (
            "3",
            "🧠 Context Layer",
            "Temperature, rainfall probability, wind and other signals are interpreted according to the user's selected mode."
        ),
        (
            "4",
            "🎯 Decision Engine",
            "Weather signals are converted into practical recommendations such as umbrella decisions and suitable travel windows."
        ),
        (
            "5",
            "🤖 Conversational Layer",
            "Users can ask natural-language weather questions rather than navigating raw weather data."
        ),
        (
            "6",
            "⚠️ Risk & Alerts",
            "Potential weather risks are summarized into understandable levels and actions."
        ),
    ]

    for number, title, description in steps:

        st.markdown(
            f"""
            <div class="weather-card" style="margin-bottom:13px;">

                <div style="
                    display:flex;
                    gap:18px;
                    align-items:flex-start;
                ">

                    <div style="
                        width:42px;
                        height:42px;
                        border-radius:50%;
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        background:linear-gradient(
                            135deg,#2d7cff,#7657ff
                        );
                        font-weight:800;
                    ">
                        {number}
                    </div>

                    <div>

                        <div style="
                            font-size:20px;
                            font-weight:800;
                        ">
                            {title}
                        </div>

                        <div style="
                            color:#91a6bf;
                            margin-top:6px;
                            line-height:1.6;
                        ">
                            {description}
                        </div>

                    </div>

                </div>

            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="section-title">🏆 Hackathon Differentiator</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="action-card">

            <div style="
                font-size:23px;
                font-weight:800;
            ">
                WeatherGPT is not only a weather display.
            </div>

            <div style="
                color:#a5b7cc;
                line-height:1.8;
                margin-top:10px;
            ">
                The platform connects <b>live weather</b>,
                <b>natural-language interaction</b>,
                <b>personal context</b>,
                <b>risk interpretation</b> and
                <b>action recommendations</b>.
                <br><br>
                This changes the interaction from:
                <b>"What is the weather?"</b>
                to:
                <b>"What should I do because of the weather?"</b>
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown(
    """
    <div class="footer-note">
        🌦️ WeatherGPT • Intelligent Weather Platform •
        Live weather + conversational interaction + personalized decisions
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# SAFE NAVIGATION FALLBACK
# ============================================================
# If a browser/session restores an old page name, return to Dashboard
# instead of leaving a blank Explore area.
if st.session_state.page not in {
    "Dashboard", "WeatherGPT AI", "Voice Assistant",
    "Smart Planner", "Forecast", "Smart Alerts", "How It Works"
}:
    st.session_state.page = "Dashboard"
    st.rerun()
