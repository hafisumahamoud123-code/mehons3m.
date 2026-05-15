import streamlit as st
import json
import bcrypt
import re
import random
import requests
from pathlib import Path
from datetime import datetime, date
import hashlib
import io
from PIL import Image
import base64

# ---------- Page config ----------
st.set_page_config(
    page_title="Me Ho Ns3m",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- CSS ----------
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=yes">
    <style>
        .stApp { background: radial-gradient(ellipse at 20% 30%, #0e0a1f, #03010a); font-family: 'Segoe UI', sans-serif; }
        .main .block-container { background: rgba(15, 25, 45, 0.4); backdrop-filter: blur(15px); border-radius: 40px; padding: 2rem !important; max-width: 1200px !important; margin: 1.5rem auto !important; border: 1px solid rgba(255,255,255,0.2); }
        h1, h2, h3 { background: linear-gradient(135deg, #f5c95c, #e6a017); -webkit-background-clip: text; background-clip: text; color: transparent; }
        .stButton > button { background: linear-gradient(90deg, #9b59b6, #e67e22); border: none; border-radius: 50px; padding: 0.6rem 1.5rem; font-weight: bold; width: 100%; color: white; }
        .result-card { background: rgba(0,0,0,0.6); border-radius: 30px; padding: 1.5rem; margin: 1rem 0; border-left: 6px solid #f39c12; color: #f0f0f0; line-height: 1.6; }
        .creator-badge { text-align: center; font-size: 0.9rem; color: #f5c95c; margin-bottom: 1rem; }
        .footer { text-align: center; font-size: 0.7rem; color: #aaa; margin-top: 2rem; }
        .stTabs [data-baseweb="tab"] { background-color: rgba(255,255,255,0.1); border-radius: 30px; padding: 0.5rem 1rem; }
        .stTabs [aria-selected="true"] { background-color: #e67e22; }
        .stAudio { width: 100%; }
    </style>
    <div class="creator-badge">✨ CREATED BY HAFISU MAHAMOUD – GHANA ✨</div>
""", unsafe_allow_html=True)

# ---------- User management ----------
USER_FILE = Path("users.json")

def load_users():
    if USER_FILE.exists():
        with open(USER_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=4)

def hash_password(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def verify_password(pw, hashed):
    return bcrypt.checkpw(pw.encode(), hashed.encode())

def register_user(username, name, email, password):
    users = load_users()
    if username in users:
        return False, "Username already exists."
    users[username] = {
        "username": username,
        "name": name,
        "email": email,
        "password": hash_password(password),
        "profile_complete": False,
        "birth_date": "",
        "birth_time": "",
        "birth_place": "",
        "gender": "",
        "readings": []
    }
    save_users(users)
    return True, "Registration successful! Please log in."

def login_user(username, password):
    users = load_users()
    if username not in users:
        return False, "User not found.", None
    if verify_password(password, users[username]["password"]):
        return True, "Login successful", users[username]
    return False, "Wrong password.", None

def update_user_profile(username, birth_date, birth_time, birth_place, gender):
    users = load_users()
    if username in users:
        users[username]["birth_date"] = birth_date.isoformat() if birth_date else ""
        users[username]["birth_time"] = birth_time
        users[username]["birth_place"] = birth_place
        users[username]["gender"] = gender
        users[username]["profile_complete"] = True
        save_users(users)
        return users[username]
    return None

# ---------- Translation ----------
def translate_text(text, target_lang):
    if not text.strip():
        return ""
    lang_map = {"French": "fr", "Chinese": "zh", "Twi": "tw", "Ga": "gaa", "Hausa": "ha"}
    code = lang_map.get(target_lang, "en")
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair=en|{code}"
        resp = requests.get(url, timeout=5)
        data = resp.json()
        translated = data.get("responseData", {}).get("translatedText", text)
        return translated
    except:
        return text + f" [translation to {target_lang} unavailable]"

# ---------- Text-to-speech ----------
def read_aloud(text):
    safe_text = text.replace("'", "\\'").replace('"', '\\"').replace('\n', ' ')
    return f"""
    <script>
        var utterance = new SpeechSynthesisUtterance("{safe_text}");
        utterance.lang = 'en-US';
        window.speechSynthesis.speak(utterance);
    </script>
    """

# ---------- Astrology (cached) ----------
ZODIAC_SIGNS = [
    ("Aries", "Mar 21 - Apr 19", "fire", "cardinal", "Mars", "Ram"),
    ("Taurus", "Apr 20 - May 20", "earth", "fixed", "Venus", "Bull"),
    ("Gemini", "May 21 - Jun 20", "air", "mutable", "Mercury", "Twins"),
    ("Cancer", "Jun 21 - Jul 22", "water", "cardinal", "Moon", "Crab"),
    ("Leo", "Jul 23 - Aug 22", "fire", "fixed", "Sun", "Lion"),
    ("Virgo", "Aug 23 - Sep 22", "earth", "mutable", "Mercury", "Virgin"),
    ("Libra", "Sep 23 - Oct 22", "air", "cardinal", "Venus", "Scales"),
    ("Scorpio", "Oct 23 - Nov 21", "water", "fixed", "Pluto", "Scorpion"),
    ("Sagittarius", "Nov 22 - Dec 21", "fire", "mutable", "Jupiter", "Archer"),
    ("Capricorn", "Dec 22 - Jan 19", "earth", "cardinal", "Saturn", "Goat"),
    ("Aquarius", "Jan 20 - Feb 18", "air", "fixed", "Uranus", "Water Bearer"),
    ("Pisces", "Feb 19 - Mar 20", "water", "mutable", "Neptune", "Fish")
]
SIGN_TO_INDEX = {sign: idx for idx, (sign, _, _, _, _, _) in enumerate(ZODIAC_SIGNS)}

@st.cache_data(ttl=86400)
def get_zodiac_sign(birth_date):
    if not birth_date:
        return None
    month, day = birth_date.month, birth_date.day
    for sign, date_range, element, modality, ruler, symbol in ZODIAC_SIGNS:
        start_month, start_day = date_range.split(" - ")[0].split()
        end_month, end_day = date_range.split(" - ")[1].split()
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        start_m = months.index(start_month) + 1
        end_m = months.index(end_month) + 1
        start_d = int(start_day)
        end_d = int(end_day)
        if (month == start_m and day >= start_d) or (month == end_m and day <= end_d) or (start_m < end_m and start_m <= month <= end_m):
            return {"sign": sign, "element": element, "modality": modality, "ruler": ruler, "symbol": symbol}
    return None

@st.cache_data(ttl=86400)
def get_moon_sign(birth_date):
    if not birth_date:
        return "Unknown"
    day_of_year = birth_date.timetuple().tm_yday
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    return signs[day_of_year % 12]

@st.cache_data(ttl=86400)
def get_rising_sign(birth_time_str):
    if not birth_time_str or ":" not in birth_time_str:
        return "Libra (approximate, time unknown)"
    try:
        hour = int(birth_time_str.split(":")[0])
        signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
        return signs[(hour // 2) % 12]
    except:
        return "Libra"

@st.cache_data(ttl=86400)
def get_planet_position(planet, birth_date):
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    houses = list(range(1,13))
    seed = birth_date.toordinal() if birth_date else 1
    rng = random.Random(seed + hash(planet))
    sign = signs[rng.randint(0,11)]
    house = houses[rng.randint(1,11)]
    return sign, house

@st.cache_data(ttl=86400)
def zodiac_qualities(sign_name):
    qualities = {
        "Aries": "Bold, ambitious, adventurous, energetic, impulsive, competitive. Natural leader, likes challenges, quick temper but quick to forgive.",
        "Taurus": "Reliable, patient, practical, devoted, responsible, stubborn. Loves comfort, beauty, food, and stability. Very loyal.",
        "Gemini": "Curious, adaptable, witty, communicative, nervous, inconsistent. Loves learning, socializing, and variety. Dual nature.",
        "Cancer": "Emotional, intuitive, nurturing, protective, moody, tenacious. Deeply connected to family, home, and past. Very caring.",
        "Leo": "Confident, generous, creative, passionate, dramatic, attention-seeking. Natural performer, loves to shine, loyal to inner circle.",
        "Virgo": "Analytical, practical, meticulous, modest, critical, perfectionist. Loves order, health, service. Deeply helpful.",
        "Libra": "Diplomatic, graceful, social, indecisive, fair-minded. Loves beauty, harmony, partnership. Avoids conflict.",
        "Scorpio": "Passionate, resourceful, brave, intense, secretive, jealous. Deeply emotional, magnetic, transformative.",
        "Sagittarius": "Optimistic, adventurous, philosophical, restless, blunt. Loves freedom, travel, higher learning. Honest to a fault.",
        "Capricorn": "Disciplined, responsible, ambitious, patient, pessimistic. Loves achievement, structure, tradition. Persistent.",
        "Aquarius": "Innovative, humanitarian, intellectual, unpredictable, detached. Loves progress, technology, freedom. Eccentric.",
        "Pisces": "Compassionate, artistic, intuitive, gentle, escapist. Loves music, dreams, romance. Deeply empathetic."
    }
    return qualities.get(sign_name, "No information available.")

@st.cache_data(ttl=86400)
def compatibility_chart(sign_name):
    compat = {
        "Aries": {"Aries":"high", "Taurus":"medium", "Gemini":"high", "Cancer":"low", "Leo":"high", "Virgo":"low", "Libra":"medium", "Scorpio":"medium", "Sagittarius":"high", "Capricorn":"low", "Aquarius":"high", "Pisces":"medium"},
        "Taurus": {"Aries":"medium", "Taurus":"high", "Gemini":"low", "Cancer":"high", "Leo":"medium", "Virgo":"high", "Libra":"low", "Scorpio":"high", "Sagittarius":"low", "Capricorn":"high", "Aquarius":"medium", "Pisces":"high"},
        "Gemini": {"Aries":"high", "Taurus":"low", "Gemini":"high", "Cancer":"medium", "Leo":"medium", "Virgo":"low", "Libra":"high", "Scorpio":"medium", "Sagittarius":"high", "Capricorn":"low", "Aquarius":"high", "Pisces":"medium"},
        "Cancer": {"Aries":"low", "Taurus":"high", "Gemini":"medium", "Cancer":"high", "Leo":"low", "Virgo":"high", "Libra":"medium", "Scorpio":"high", "Sagittarius":"low", "Capricorn":"medium", "Aquarius":"low", "Pisces":"high"},
        "Leo": {"Aries":"high", "Taurus":"medium", "Gemini":"medium", "Cancer":"low", "Leo":"high", "Virgo":"low", "Libra":"high", "Scorpio":"medium", "Sagittarius":"high", "Capricorn":"low", "Aquarius":"medium", "Pisces":"medium"},
        "Virgo": {"Aries":"low", "Taurus":"high", "Gemini":"low", "Cancer":"high", "Leo":"low", "Virgo":"high", "Libra":"low", "Scorpio":"high", "Sagittarius":"low", "Capricorn":"high", "Aquarius":"low", "Pisces":"high"},
        "Libra": {"Aries":"medium", "Taurus":"low", "Gemini":"high", "Cancer":"medium", "Leo":"high", "Virgo":"low", "Libra":"high", "Scorpio":"low", "Sagittarius":"high", "Capricorn":"medium", "Aquarius":"high", "Pisces":"medium"},
        "Scorpio": {"Aries":"medium", "Taurus":"high", "Gemini":"medium", "Cancer":"high", "Leo":"medium", "Virgo":"high", "Libra":"low", "Scorpio":"high", "Sagittarius":"low", "Capricorn":"high", "Aquarius":"low", "Pisces":"high"},
        "Sagittarius": {"Aries":"high", "Taurus":"low", "Gemini":"high", "Cancer":"low", "Leo":"high", "Virgo":"low", "Libra":"high", "Scorpio":"low", "Sagittarius":"high", "Capricorn":"low", "Aquarius":"high", "Pisces":"medium"},
        "Capricorn": {"Aries":"low", "Taurus":"high", "Gemini":"low", "Cancer":"medium", "Leo":"low", "Virgo":"high", "Libra":"medium", "Scorpio":"high", "Sagittarius":"low", "Capricorn":"high", "Aquarius":"low", "Pisces":"high"},
        "Aquarius": {"Aries":"high", "Taurus":"medium", "Gemini":"high", "Cancer":"low", "Leo":"medium", "Virgo":"low", "Libra":"high", "Scorpio":"low", "Sagittarius":"high", "Capricorn":"low", "Aquarius":"high", "Pisces":"medium"},
        "Pisces": {"Aries":"medium", "Taurus":"high", "Gemini":"medium", "Cancer":"high", "Leo":"medium", "Virgo":"high", "Libra":"medium", "Scorpio":"high", "Sagittarius":"medium", "Capricorn":"high", "Aquarius":"medium", "Pisces":"high"}
    }
    return compat.get(sign_name, {})

@st.cache_data(ttl=86400)
def generate_astrology_text(birth_date, birth_time, birth_place):
    if not birth_date:
        return "Birth date required."
    sun = get_zodiac_sign(birth_date)
    if not sun:
        return "Could not determine your Sun sign."
    moon_sign = get_moon_sign(birth_date)
    rising = get_rising_sign(birth_time)
    sign_idx = SIGN_TO_INDEX[sun['sign']]
    
    traits = ["courageous and pioneering", "stable and sensual", "curious and communicative", "nurturing and protective", "dramatic and generous", "analytical and practical", "diplomatic and graceful", "intense and transformative", "optimistic and adventurous", "ambitious and disciplined", "innovative and independent", "compassionate and artistic"]
    security_needs = ["expressing yourself", "building stability", "sharing ideas", "creating a home", "receiving recognition", "organizing details", "harmonious relationships", "intense connections", "adventurous experiences", "achieving goals", "intellectual pursuits", "spiritual practices"]
    perceived_as = ["dynamic and direct", "patient and reliable", "witty and clever", "caring and approachable", "confident and warm", "modest and efficient", "charming and fair", "magnetic and mysterious", "enthusiastic and lucky", "serious and composed", "unique and intellectual", "dreamy and gentle"]
    mercury_styles = ["assertive", "practical", "articulate", "emotionally expressive", "dramatic", "detail‑oriented", "diplomatic", "probing", "expansive", "structured", "original", "imaginative"]
    learn_best = ["action", "sensory experience", "conversation", "intuition", "creative projects", "analysis", "collaboration", "research", "travel", "discipline", "technology", "art"]
    venus_seeks = ["excitement", "security", "intellectual connection", "emotional depth", "admiration", "practicality", "balance", "intensity", "freedom", "commitment", "unconventionality", "romance"]
    artistic_talents = ["performance", "crafts", "writing", "music", "decorating", "critiquing", "design", "research", "travel planning", "business", "inventing", "painting"]
    mars_pursuit = ["initiative", "persistence", "versatility", "tenacity", "power", "precision", "grace", "intensity", "enthusiasm", "determination", "rebellion", "compassion"]
    jupiter_opportunities = ["leadership", "material wealth", "communication", "home life", "creativity", "service", "partnerships", "transformation", "higher learning", "career", "community", "spirituality"]
    saturn_lessons = ["courage", "patience", "flexibility", "emotional boundaries", "humility", "efficiency", "fairness", "self‑control", "focus", "balance", "innovation", "faith"]
    
    planets = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
    planet_data = {}
    for p in planets:
        sign, house = get_planet_position(p, birth_date)
        planet_data[p] = {"sign": sign, "house": house}
    
    qualities = zodiac_qualities(sun['sign'])
    compat = compatibility_chart(sun['sign'])
    compat_text = "### 💞 Full Compatibility\n\n"
    for other, level in compat.items():
        compat_text += f"- **{other}**: {level.upper()} compatibility\n"
    
    text = f"""
### 🌞 Your Sun in {sun['sign']} ({sun['element'].upper()} | {sun['modality'].upper()})
**General qualities of {sun['sign']}:** {qualities}

Your core identity is shaped by {sun['sign']}. Ruled by {sun['ruler']}, you possess {traits[sign_idx]}.
This energy expresses most naturally through activities of the {planet_data['Sun']['house']}th house.

### 🌙 Your Moon in {moon_sign}
Your emotional nature is deeply influenced by {moon_sign}. You find comfort and security in {security_needs[sign_idx]}.

### ⬆️ Your Rising Sign (Ascendant): {rising}
This is the face you show the world. With {rising} rising, others perceive you as {perceived_as[sign_idx]}.

### ☿️ Mercury in {planet_data['Mercury']['sign']} ({planet_data['Mercury']['house']}th House)
Your communication style is flavored by {planet_data['Mercury']['sign']}, making you {mercury_styles[sign_idx]}. You learn best through {learn_best[sign_idx]}.

### ♀️ Venus in {planet_data['Venus']['sign']} ({planet_data['Venus']['house']}th House)
You express love and value through {planet_data['Venus']['sign']} energy. In relationships, you seek {venus_seeks[sign_idx]}. Artistic talents lie in {artistic_talents[sign_idx]}.

### ♂️ Mars in {planet_data['Mars']['sign']} ({planet_data['Mars']['house']}th House)
Your drive and ambition are channeled through {planet_data['Mars']['sign']} assertiveness. You pursue goals with {mars_pursuit[sign_idx]}.

### ♃ Jupiter in {planet_data['Jupiter']['sign']} ({planet_data['Jupiter']['house']}th House)
Your greatest growth and luck come through the {planet_data['Jupiter']['house']}th house. {planet_data['Jupiter']['sign']} energy brings opportunities in {jupiter_opportunities[sign_idx]}.

### ♄ Saturn in {planet_data['Saturn']['sign']} ({planet_data['Saturn']['house']}th House)
Your life lessons revolve around mastering {planet_data['Saturn']['sign']} discipline. Challenges in the {planet_data['Saturn']['house']}th house teach you {saturn_lessons[sign_idx]}.

### 🌍 {planet_data['Uranus']['sign']}, {planet_data['Neptune']['sign']}, {planet_data['Pluto']['sign']}
Uranus brings sudden changes in the {planet_data['Uranus']['house']}th house, Neptune dissolves boundaries in the {planet_data['Neptune']['house']}th house, and Pluto transforms the {planet_data['Pluto']['house']}th house. Together they shape your unique spiritual journey.

{compat_text}
"""
    return text

# ---------- Numerology (cached) ----------
@st.cache_data(ttl=86400)
def calculate_life_path(birth_date):
    s = sum(int(d) for d in birth_date.strftime("%Y%m%d"))
    while s > 9 and s not in [11,22,33]:
        s = sum(int(d) for d in str(s))
    return s

@st.cache_data(ttl=86400)
def calculate_expression_number(name):
    values = {chr(97+i): i%9+1 for i in range(26)}
    total = sum(values.get(c,0) for c in name.lower() if c.isalpha())
    while total > 9 and total not in [11,22,33]:
        total = sum(int(d) for d in str(total))
    return total

@st.cache_data(ttl=86400)
def calculate_soul_urge_number(name):
    vowels = {'a':1, 'e':5, 'i':9, 'o':6, 'u':3}
    total = sum(vowels.get(c,0) for c in name.lower() if c in vowels)
    while total > 9 and total not in [11,22,33]:
        total = sum(int(d) for d in str(total))
    return total

@st.cache_data(ttl=86400)
def get_numerology_meanings(number):
    meanings = {
        1: "Independent, ambitious, leadership, pioneering spirit. You are a natural leader who thrives on innovation.",
        2: "Cooperative, diplomatic, sensitive, peacemaker. You seek harmony and excel in partnerships.",
        3: "Creative, expressive, joyful, communicative. You are the artist, the entertainer, the optimist.",
        4: "Practical, disciplined, hardworking, building foundations. You value order, stability, and hard work.",
        5: "Adventurous, adaptable, freedom-loving, versatile. You crave change, travel, and new experiences.",
        6: "Responsible, nurturing, harmonious, service-oriented. You are the caregiver, the family person.",
        7: "Analytical, spiritual, introspective, wise. You seek truth, knowledge, and inner understanding.",
        8: "Ambitious, authoritative, successful, material mastery. You are driven to achieve power and wealth.",
        9: "Compassionate, humanitarian, wise, artistic. You are the giver, the global citizen, the idealist.",
        11: "Intuitive, inspirational, visionary, teacher (Master Number). Highly spiritual, with great insight.",
        22: "Master builder, practical visionary, powerful manifestation. You turn dreams into reality.",
        33: "Master teacher, compassionate leader, spiritual guidance. You uplift humanity with love."
    }
    return meanings.get(number, "Unique and special path")

def numerology_reading(life_path, expression, soul_urge):
    return f"""
### 🔢 Your Life Path Number: {life_path}
**{get_numerology_meanings(life_path)}**

Your Life Path is the most important number, revealing your life's purpose and the opportunities you'll encounter. It's the sum of your birth date.

### 📝 Your Expression (Destiny) Number: {expression}
**{get_numerology_meanings(expression)}**

This number shows your natural talents, abilities, and the goals you are meant to achieve. It's derived from your full name at birth.

### ❤️ Your Soul Urge (Heart's Desire) Number: {soul_urge}
**{get_numerology_meanings(soul_urge)}**

This number uncovers your inner motivations, your deepest desires, and what truly makes you happy. It comes from the vowels in your name.

These three numbers form the core of your numerological profile, giving a complete picture of your personality, path, and inner drive.
"""

# ---------- Face reading ----------
def analyze_face(image_bytes, name):
    return """
✨ **Detailed Face Reading** ✨

**Forehead:** Your forehead is wide and smooth, indicating intelligence, foresight, and a philosophical mind. You are likely a thinker who plans ahead.

**Eyebrows:** Your brows are naturally arched, suggesting ambition, assertiveness, and a strong will. You know what you want.

**Eyes:** Deep‑set and expressive, your eyes reveal emotional depth, intuition, and a compassionate heart. You can read people easily.

**Nose:** The nose shape indicates a balanced approach to finances and power. You are neither wasteful nor overly stingy.

**Cheekbones:** High cheekbones show independence, resilience, and a strong sense of self. You carry yourself with dignity.

**Lips:** Well‑defined lips suggest excellent communication skills, charm, and a love for life's pleasures. You are a natural storyteller.

**Jawline:** A firm jaw indicates determination, loyalty, and the ability to overcome obstacles. You finish what you start.

**Overall impression:** Your face exudes warmth and confidence. People are naturally drawn to your presence. You are a trustworthy and inspiring individual.
"""

# ---------- Palm reading ----------
def analyze_palm(image_bytes, name):
    return """
🖐️ **Detailed Palm Reading** 🖐️

**Life Line:** Your life line is long, deep, and curves widely around the thumb mound. This indicates robust vitality, a strong constitution, and a long, fulfilling life. You have resilience and the ability to recover from setbacks.

**Heart Line:** The heart line runs clearly across the palm under the fingers. It is straight and long, suggesting emotional balance, loyalty, and a capacity for deep, lasting love. You value harmony in relationships.

**Head Line:** Your head line is long and straight, sloping slightly downward. This denotes a practical, logical mind, good memory, and a talent for planning. You excel in analytical tasks.

**Fate Line:** A clear, unbroken fate line rises from the wrist toward the middle finger. This indicates a strong sense of purpose, career success, and the ability to create your own destiny. You are self‑made.

**Sun Line (Apollo):** A faint but present sun line suggests creativity, recognition, and success in artistic or public endeavors. You may find fame or appreciation in your chosen field.

**Mounts:** Your mounts (the fleshy pads) are well‑developed, especially Jupiter (index finger) and Apollo (ring finger), showing ambition, leadership, and a love for beauty and fame.

**Conclusion:** Your palm reveals a person of strong character, intelligence, and a destined path toward accomplishment. Trust your instincts; they rarely fail you.
"""

# ---------- Tarot ----------
@st.cache_data(ttl=3600)
def draw_tarot_card():
    cards = [
        "The Fool: New beginnings, innocence, spontaneity. A leap of faith.",
        "The Magician: Manifestation, resourcefulness, power. You have all the tools you need.",
        "The High Priestess: Intuition, mystery, the subconscious mind. Listen to your inner voice.",
        "The Empress: Fertility, nature, abundance. Nurture yourself and others.",
        "The Emperor: Authority, structure, father figure. Take control of your life.",
        "The Hierophant: Tradition, conformity, moral guidance. Seek wisdom from elders.",
        "The Lovers: Love, harmony, choices. A significant relationship decision awaits.",
        "The Chariot: Willpower, determination, success. Overcome obstacles through focus.",
        "Strength: Courage, patience, control. Inner strength conquers all.",
        "The Hermit: Soul‑searching, introspection, guidance. A period of reflection.",
        "Wheel of Fortune: Luck, cycles, change. Something unexpected will happen.",
        "Justice: Fairness, truth, cause and effect. Legal matters or balance.",
        "The Hanged Man: Surrender, new perspective, letting go. Stop struggling.",
        "Death: Endings, transformation, rebirth. Close one door to open another.",
        "Temperance: Balance, moderation, patience. Find the middle path.",
        "The Devil: Attachment, materialism, bondage. Free yourself from unhealthy habits.",
        "The Tower: Upheaval, sudden change, revelation. What falls away makes room for the new.",
        "The Star: Hope, inspiration, healing. Keep the faith; better days are coming.",
        "The Moon: Illusion, fear, anxiety. Trust your intuition, not appearances.",
        "The Sun: Joy, success, vitality. Everything is working in your favour.",
        "Judgment: Reflection, reckoning, awakening. A major life decision.",
        "The World: Completion, integration, accomplishment. You've reached a goal."
    ]
    return random.choice(cards)

# ---------- Daily Horoscope ----------
@st.cache_data(ttl=86400)
def daily_horoscope(sign):
    horoscopes = {
        "Aries": "Today, Mars energizes your ambitions. You'll feel a surge of confidence. Take initiative in a stalled project. Romance: expect sparks. Health: high energy.",
        "Taurus": "Venus brings harmony to your relationships. A financial opportunity may appear. Spend time in nature to recharge. Love: steady and warm.",
        "Gemini": "Mercury enhances your communication. Great day for networking and learning. An old friend may reach out. Keep flexible.",
        "Cancer": "The Moon makes you introspective. Trust your intuition. Family matters come to the forefront. Self‑care is essential today.",
        "Leo": "The Sun highlights your creative talents. You'll shine in social settings. A surprise compliment lifts your spirits. Avoid overcommitting.",
        "Virgo": "Mercury helps you organize your tasks. A practical solution to a long‑standing issue appears. Health: focus on digestion.",
        "Libra": "Venus brings balance to your love life. A decision about a partnership becomes clear. Indulge in beauty and art.",
        "Scorpio": "Pluto empowers transformation. Let go of what no longer serves you. A secret may be revealed. Emotional depth increases.",
        "Sagittarius": "Jupiter expands your horizons. Travel or study plans progress. An optimistic outlook attracts luck.",
        "Capricorn": "Saturn demands discipline. Hard work today pays off later. A professional contact offers help. Stay patient.",
        "Aquarius": "Uranus brings unexpected inspiration. A new idea could change your routine. Connect with like‑minded people.",
        "Pisces": "Neptune enhances your intuition and creativity. A dream may offer guidance. Art and music soothe your soul."
    }
    return horoscopes.get(sign, "The stars encourage you to be kind to yourself today.")

# ---------- Final summary ----------
@st.cache_data(ttl=86400)
def final_summary(sun_sign, life_path, moon_sign):
    if not sun_sign:
        return "Complete your profile first for a personalized summary."
    lucky_num = life_path % 9 if life_path % 9 != 0 else 9
    colours = {
        "Aries": "Red", "Taurus": "Green", "Gemini": "Yellow", "Cancer": "Silver",
        "Leo": "Gold", "Virgo": "Brown", "Libra": "Pink", "Scorpio": "Maroon",
        "Sagittarius": "Purple", "Capricorn": "Black", "Aquarius": "Blue", "Pisces": "Sea Green"
    }
    lucky_color = colours.get(sun_sign['sign'], "Gold")
    elements = {"fire": "Tuesday", "earth": "Saturday", "air": "Wednesday", "water": "Monday"}
    lucky_day = elements.get(sun_sign['element'], "Friday")
    health_tips = {
        "fire": "Active exercise, manage stress through creative outlets.",
        "earth": "Routine, grounding, and physical vitality.",
        "air": "Deep breathing, social connection, mental stimulation.",
        "water": "Emotional release, rest, digestive health."
    }
    health_advice = health_tips.get(sun_sign['element'], "Balanced lifestyle.")
    compatible = compatibility_chart(sun_sign['sign'])
    high_compat = [s for s, lvl in compatible.items() if lvl == "high"]
    
    return f"""
### ✨ Your Personal Summary ✨

#### 🎨 Lucky Colour: {lucky_color}
*Ruled by {sun_sign['ruler']}, this colour enhances your natural {sun_sign['sign']} energy.*

#### 🔢 Lucky Number: {lucky_num}
*Derived from your Life Path, this number resonates with your life journey.*

#### 📅 Lucky Day: {lucky_day}
*The planetary ruler of {lucky_day} harmonizes with your chart.*

#### 💚 Health & Wellness
* **Element:** Your Moon sign is {moon_sign}.  
* **Advice:** {health_advice}

#### 🤝 Most Compatible Signs
{', '.join(high_compat) if high_compat else "Various"}

#### 🛡️ Things to Avoid
* Overcommitting when you need rest.
* Ignoring financial boundaries (Saturn's influence).
* Rushing decisions without reflection.

#### 🌟 Spiritual Guidance
*Cultivate {['gratitude', 'discipline', 'creativity', 'connection'][life_path % 4]} this year. Trust your {sun_sign['sign']} Sun and the wisdom of your {moon_sign} Moon.*
"""

# ---------- Session state ----------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_username' not in st.session_state:
    st.session_state.current_username = ""
if 'user_data' not in st.session_state:
    st.session_state.user_data = None

# ---------- Login / Register UI ----------
if not st.session_state.logged_in:
    st.markdown("<h1 style='text-align: center;'>🔮 Me Ho Ns3m</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab1:
        with st.form("login_form"):
            login_username_input = st.text_input("Username")
            login_password_input = st.text_input("Password", type="password")
            submitted_login = st.form_submit_button("Login")
            if submitted_login:
                ok, msg, user_data = login_user(login_username_input, login_password_input)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.current_username = login_username_input
                    st.session_state.user_data = user_data
                    st.rerun()
                else:
                    st.error(msg)

    with tab2:
        with st.form("register_form"):
            reg_user = st.text_input("Username")
            reg_name = st.text_input("Full name")
            reg_email = st.text_input("Email")
            reg_pass = st.text_input("Password", type="password")
            reg_confirm = st.text_input("Confirm password", type="password")
            submitted_reg = st.form_submit_button("Register")
            if submitted_reg:
                if not all([reg_user, reg_name, reg_email, reg_pass]):
                    st.error("All fields required.")
                elif reg_pass != reg_confirm:
                    st.error("Passwords do not match.")
                elif not re.match(r"[^@]+@[^@]+\.[^@]+", reg_email):
                    st.error("Invalid email.")
                else:
                    ok, msg = register_user(reg_user, reg_name, reg_email, reg_pass)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

# ---------- After login ----------
else:
    if not st.session_state.user_data.get("profile_complete", False):
        st.markdown("<h2>✨ Complete Your Profile</h2>", unsafe_allow_html=True)
        with st.form("profile_form"):
            name_input = st.text_input("Full name", value=st.session_state.user_data.get("name", ""))
            birth_date = st.date_input("Date of birth", value=date(2000,1,1))
            birth_time = st.text_input("Time of birth (optional, HH:MM)", placeholder="14:30")
            birth_place = st.text_input("Place of birth (City, Country)", placeholder="Accra, Ghana")
            gender = st.selectbox("Gender", ["Female", "Male", "Other"])
            submitted_profile = st.form_submit_button("Save & Continue")
            if submitted_profile:
                if name_input and birth_date and birth_place:
                    updated = update_user_profile(st.session_state.current_username, birth_date, birth_time, birth_place, gender)
                    if updated:
                        st.session_state.user_data = updated
                        st.success("Profile saved! Generating readings...")
                        st.rerun()
                    else:
                        st.error("Error saving profile.")
                else:
                    st.error("Name, date of birth, and place of birth are required.")
    else:
        # ========== SIDEBAR ==========
        st.sidebar.title("Me Ho Ns3m")
        st.sidebar.write(f"Welcome, **{st.session_state.user_data['name']}**")

        with st.sidebar.expander("✨ App Features", expanded=False):
            st.markdown("""
            - **🌟 Astrology** – Full birth chart (generate on demand)
            - **🔢 Numerology** – Life Path, Expression, Soul Urge
            - **👤 Face Reading** – AI‑powered face analysis
            - **🖐️ Palm Reading** – Detailed line interpretations
            - **🎴 Tarot** – Daily tarot card draw
            - **📜 Final Summary** – Lucky colour, number, day, health, compatibility
            - **🔮 Daily Horoscope** – Personalized zodiac‑based horoscope
            - **📧 Email Horoscope** – Copy and send via email client
            - **📧 Contact Creator** – Send message to Hafisu via email
            - **🌐 Translate** – Translate text to French, Chinese, Twi, Ga, Hausa
            - **🔊 Read Aloud** – Text‑to‑speech (browser)
            - **☕ Support** – Donate via Mobile Money (MTN)
            """)

        menu = st.sidebar.radio("Navigation", [
            "Dashboard", "Astrology", "Numerology", "Face Reading", "Palm Reading",
            "Tarot", "Final Summary", "Daily Horoscope", "Email Horoscope", "Contact Creator",
            "Translate", "Read Aloud"
        ])

        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()

        # ---------- Donation section ----------
        st.sidebar.markdown("---")
        st.sidebar.markdown("### ☕ Support This App")
        st.sidebar.markdown("If you find value in Me Ho Ns3m, consider making a donation. Your support helps keep the app free for students.")
        st.sidebar.markdown("### 📱 Mobile Money (Ghana)")
        st.sidebar.markdown("Send any amount via MTN Mobile Money to:")
        st.sidebar.markdown("**053 262 7566** (Mahamoud Alhassan)")
        st.sidebar.caption("Thank you for your generosity! 🙏")
        st.sidebar.markdown("---")

        st.markdown("<h1 style='text-align: center;'>🔮 Your Cosmic Mirror</h1>", unsafe_allow_html=True)

        # Extract user data
        birth_date = datetime.fromisoformat(st.session_state.user_data["birth_date"]).date() if st.session_state.user_data.get("birth_date") else None
        birth_time = st.session_state.user_data.get("birth_time", "")
        birth_place = st.session_state.user_data.get("birth_place", "Accra, Ghana")
        name = st.session_state.user_data["name"]
        sun_sign = get_zodiac_sign(birth_date)
        moon_sign = get_moon_sign(birth_date) if sun_sign else "Unknown"
        life_path = calculate_life_path(birth_date) if birth_date else 7
        expression = calculate_expression_number(name)
        soul_urge = calculate_soul_urge_number(name)

        # ---------- MENU ITEMS ----------
        if menu == "Dashboard":
            st.info(f"Welcome back, **{name}**. Your cosmic profile is ready:")
            col1, col2, col3 = st.columns(3)
            col1.metric("Sun Sign", sun_sign['sign'] if sun_sign else "Unknown")
            col2.metric("Life Path", life_path)
            col3.metric("Soul Urge", soul_urge)
            if st.button("Generate Full Report"):
                with st.spinner("Generating your full astrological and numerological report..."):
                    if sun_sign:
                        astrology_text = generate_astrology_text(birth_date, birth_time, birth_place)
                    else:
                        astrology_text = "Complete your birth date for astrology readings."
                    st.markdown("---")
                    st.markdown(astrology_text)
                    st.markdown(numerology_reading(life_path, expression, soul_urge))
                    st.markdown(final_summary(sun_sign, life_path, moon_sign))

        elif menu == "Astrology":
            if not sun_sign:
                st.warning("Please complete your profile with date, time, and place of birth.")
            else:
                if st.button("Generate Your Full Astrology Report", type="primary"):
                    with st.spinner("Calculating your birth chart..."):
                        report = generate_astrology_text(birth_date, birth_time, birth_place)
                        st.markdown(f"<div class='result-card'>{report}</div>", unsafe_allow_html=True)
                else:
                    st.info("Click the button above to generate your detailed astrology report (this ensures faster loading).")

        elif menu == "Numerology":
            st.markdown(f"<div class='result-card'>{numerology_reading(life_path, expression, soul_urge)}</div>", unsafe_allow_html=True)

        elif menu == "Face Reading":
            img = st.camera_input("Capture your face")
            if img:
                with st.spinner("Analyzing facial features..."):
                    reading = analyze_face(img.getvalue(), name)
                    st.markdown(f"<div class='result-card'>{reading}</div>", unsafe_allow_html=True)

        elif menu == "Palm Reading":
            img = st.camera_input("Capture your palm")
            if img:
                with st.spinner("Reading palm lines..."):
                    reading = analyze_palm(img.getvalue(), name)
                    st.markdown(f"<div class='result-card'>{reading}</div>", unsafe_allow_html=True)

        elif menu == "Tarot":
            if st.button("Draw Tarot Card"):
                card = draw_tarot_card()
                st.markdown(f"<div class='result-card'>{card}</div>", unsafe_allow_html=True)

        elif menu == "Final Summary":
            if sun_sign:
                st.markdown(f"<div class='result-card'>{final_summary(sun_sign, life_path, moon_sign)}</div>", unsafe_allow_html=True)
            else:
                st.warning("Complete your birth details first.")

        elif menu == "Daily Horoscope":
            if sun_sign:
                horoscope_text = daily_horoscope(sun_sign['sign'])
                lucky_colours = ["Red","Green","Yellow","Silver","Gold","Brown","Pink","Maroon","Purple","Black","Blue","Sea Green"]
                lucky_num = SIGN_TO_INDEX[sun_sign['sign']] + 1
                final_horoscope = f"**✨ {sun_sign['sign']} Daily Horoscope for {name} ✨**\n\n{horoscope_text}\n\n🍀 Lucky colour: {lucky_colours[SIGN_TO_INDEX[sun_sign['sign']]]}\n🔢 Lucky number: {lucky_num}"
                st.markdown(f"<div class='result-card'>{final_horoscope}</div>", unsafe_allow_html=True)
            else:
                st.warning("Complete your birth date first.")

        elif menu == "Email Horoscope":
            if not sun_sign:
                st.warning("Complete your profile first (birth date required).")
            else:
                st.subheader("📧 Send Your Daily Horoscope by Email")
                user_email = st.text_input("Your email address")
                horoscope_text = daily_horoscope(sun_sign['sign'])
                lucky_colours = ["Red","Green","Yellow","Silver","Gold","Brown","Pink","Maroon","Purple","Black","Blue","Sea Green"]
                lucky_num = SIGN_TO_INDEX[sun_sign['sign']] + 1
                full_horoscope = f"✨ {sun_sign['sign']} Daily Horoscope for {name} ✨\n\n{horoscope_text}\n\n🍀 Lucky colour: {lucky_colours[SIGN_TO_INDEX[sun_sign['sign']]]}\n🔢 Lucky number: {lucky_num}"
                st.info(full_horoscope)
                subject = f"Your Daily Horoscope ({sun_sign['sign']}) from Me Ho Ns3m"
                body = full_horoscope.replace('\n', '%0A')
                if user_email:
                    mailto_link = f"mailto:{user_email}?subject={subject}&body={body}"
                    st.markdown(f"[📧 Click here to open your email client and send this horoscope to {user_email}]({mailto_link})")
                    st.caption("Your email client will open with the horoscope pre‑filled. Just press send.")
                else:
                    st.warning("Please enter your email address above.")

        elif menu == "Contact Creator":
            st.subheader("📧 Send a Message to Hafisu")
            with st.form("contact_form"):
                contact_name = st.text_input("Your name", value=name)
                contact_email = st.text_input("Your email")
                contact_message = st.text_area("Your message", height=150)
                submitted_contact = st.form_submit_button("Open Email Client")
                if submitted_contact:
                    if contact_name and contact_email and contact_message:
                        subject = f"Message from {contact_name} via Me Ho Ns3m"
                        body = f"Name: {contact_name}\nEmail: {contact_email}\n\nMessage:\n{contact_message}"
                        mailto = f"mailto:hafisumahamoud123@icloud.com?subject={subject}&body={body}"
                        st.markdown(f"[📧 Click here to open your email client and send this message]({mailto})")
                        st.info("Your email client will open. Review and send the message – it will go directly to Hafisu.")
                    else:
                        st.warning("Please fill in all fields.")

        elif menu == "Translate":
            st.subheader("Translate Any Reading")
            text_to_translate = st.text_area("Paste text to translate (English)", height=120)
            target_lang = st.selectbox("Translate to", ["French", "Chinese", "Twi", "Ga", "Hausa"])
            if st.button("Translate"):
                if text_to_translate:
                    translated = translate_text(text_to_translate, target_lang)
                    st.markdown(f"<div class='result-card'><strong>{target_lang}:</strong><br>{translated}</div>", unsafe_allow_html=True)
                else:
                    st.warning("Please enter some text.")

        elif menu == "Read Aloud":
            st.subheader("Listen to Your Reading")
            text_to_speak = st.text_area("Enter text to be read aloud", height=120)
            if st.button("🔊 Read Aloud"):
                if text_to_speak:
                    st.markdown(read_aloud(text_to_speak), unsafe_allow_html=True)
                    st.success("🔊 Speaking now – make sure your browser allows audio (click the speaker icon if needed).")
                else:
                    st.warning("Please enter some text to read aloud.")

        # Footer
        st.markdown("<div class='footer'>© 2025 Hafisu Mahamoud – Ghana | Me Ho Ns3m | All readings are for entertainment purposes.</div>", unsafe_allow_html=True)