"""Destination data and itinerary logic for the Himachal Pradesh planner.

Pure Python (standard library only), so it can be unit-tested without a web server.
main.py exposes build_itinerary() through the REST API.
"""
import math
import re

# season -> (months, base cold-risk score)
SEASONS = {
    "Spring": ("March to May", 70),
    "Summer": ("June to August", 45),
    "Autumn": ("September to November", 65),
    "Winter": ("December to February", 95),
}

# tier -> (food per head per day, stay per room per night), in rupees. Illustrative.
TIER_RATES = {"Budget": (600, 1200), "Comfort": (900, 3000), "Premium": (1500, 7500)}

# Predefined trails shown as cards on the main page
TRAILS = {
    "Triund": {"altitude_m": 2828, "km": 9, "days": 2, "level": "easy", "lon": 76.35, "lat": 32.27, "signal": 40},
    "Bhrigu Lake": {"altitude_m": 4300, "km": 20, "days": 3, "level": "moderate", "lon": 77.17, "lat": 32.35, "signal": 60},
    "Hampta Pass": {"altitude_m": 4270, "km": 26, "days": 5, "level": "moderate", "lon": 77.38, "lat": 32.27, "signal": 70},
    "Chandratal": {"altitude_m": 4300, "km": 3, "days": 2, "level": "easy", "lon": 77.61, "lat": 32.48, "signal": 85},
    "Pin Parvati Pass": {"altitude_m": 5319, "km": 110, "days": 10, "level": "hard", "lon": 77.85, "lat": 32.0, "signal": 95},
}

# Known places a visitor may type in: key -> (altitude_m, lon, lat, signal risk)
KNOWN_PLACES = {
    "chitkul": (3450, 78.43, 31.35, 55), "jibhi": (1900, 77.35, 31.59, 45),
    "kaza": (3800, 78.07, 32.22, 60), "spiti": (3800, 78.07, 32.22, 60),
    "kasol": (1640, 77.31, 32.01, 55), "manali": (2050, 77.19, 32.24, 20),
    "shimla": (2276, 77.17, 31.10, 10), "dharamshala": (1457, 76.32, 32.22, 10),
    "kalpa": (2960, 78.25, 31.54, 45), "sangla": (2680, 78.26, 31.43, 45),
    "tabo": (3280, 78.38, 32.09, 60), "keylong": (3350, 77.03, 32.57, 50),
    "chamba": (996, 76.13, 32.55, 30),
}
UNKNOWN_SIGNAL = 70  # assume remote when we know nothing about a custom place


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def round_half_up(x):
    return int(math.floor(x + 0.5))


def level(score):
    return "Low" if score < 35 else "Moderate" if score < 70 else "High"


def clean_name(raw):
    """Keep letters, digits, spaces, apostrophes, dots and hyphens; max 40 chars."""
    s = re.sub(r"[^\w\s'.\-]|_", " ", raw or "")
    return re.sub(r"\s+", " ", s).strip()[:40]


def parse_places(trails_param):
    """Comma-separated query value -> unique, cleaned names (max 12), predefined trails normalised."""
    lookup = {k.lower(): k for k in TRAILS}
    names, seen = [], set()
    for part in (trails_param or "").split(","):
        name = clean_name(part)
        name = lookup.get(name.lower(), name)
        if name and name.lower() not in seen and len(names) < 12:
            seen.add(name.lower())
            names.append(name)
    return names


def describe_place(name):
    """Return a normalised record for a trail, a known place or a custom (unknown) place."""
    if name in TRAILS:
        t = TRAILS[name]
        return {"name": name, "type": "trail", "altitude_m": t["altitude_m"], "lon": t["lon"], "lat": t["lat"],
                "days": t["days"], "km": t["km"], "level": t["level"], "signal": t["signal"]}
    known = KNOWN_PLACES.get(name.lower())
    if known:
        alt, lon, lat, sig = known
        return {"name": name, "type": "known", "altitude_m": alt, "lon": lon, "lat": lat,
                "days": 2, "km": 0, "level": None, "signal": sig}
    return {"name": name, "type": "custom", "altitude_m": 0, "lon": None, "lat": None,
            "days": 2, "km": 0, "level": None, "signal": UNKNOWN_SIGNAL}


def place_note(p):
    """Safety note for a non-trail place, with a smart fallback when nothing is known."""
    if p["type"] == "custom":
        return f"No altitude on file for {p['name']}. Confirm road access, weather and mobile signal locally before you go."
    alt = f"{p['altitude_m']:,}"
    if p["altitude_m"] > 3000:
        return f"{p['name']} sits near {alt} m. Spend a night acclimatising and expect cold evenings."
    return f"{p['name']} is at about {alt} m. Altitude is mild, but monsoon landslides can close roads from July to September."


def build_itinerary(season="Summer", trails="", travellers=2, tier="Comfort", days=None):
    season = season if season in SEASONS else "Summer"
    tier = tier if tier in TIER_RATES else "Comfort"
    names = parse_places(trails)
    fallback = not names
    if fallback:
        names = ["Hampta Pass"]
    places = [describe_place(n) for n in names]

    total_days = 1 + sum(p["days"] for p in places)  # day 1 is arrival and acclimatisation
    km = sum(p["km"] for p in places)
    max_alt = max([p["altitude_m"] for p in places] + [0])
    high = [p["name"] for p in places if p["altitude_m"] > 4000]
    months, base_cold = SEASONS[season]

    # Season advisory
    if high and season in ("Winter", "Spring"):
        status, msg = "warning", f"{', '.join(high)}: high passes are usually snowbound or closed in {season.lower()}. Consider Summer."
    elif high and season == "Autumn":
        status, msg = "warning", "High passes begin closing from late October. Go early in the season."
    else:
        status, msg = "ok", "No conflict found between your places and this season."

    # Hazard meters (0 to 100)
    cold = clamp(base_cold + (10 if max_alt > 4000 else 0), 0, 100)
    altitude = clamp(round_half_up((max_alt - 2500) / 30), 5, 100) if max_alt else 5
    signal = max(p["signal"] for p in places)
    fuel = 75 if max_alt > 4000 else 50 if any(p["type"] == "custom" for p in places) else 30
    hazards = [
        {"name": "Fuel limits", "score": fuel, "level": level(fuel),
         "message": "Tandi in Lahaul is the last dependable pump before the Leh road, and Kaza has the only one in Spiti. Fill the tank and carry a spare can."},
        {"name": "Thermal alerts", "score": cold, "level": level(cold),
         "message": "Night temperatures above 4,000 m can drop below freezing even in summer. Pack for "
                    + ("deep cold and snow." if cold >= 70 else "sharp nights and sudden storms.")},
        {"name": "Network signal", "score": signal, "level": level(signal),
         "message": "Expect no coverage at Batal, Chandratal and on the high passes. Mobile signal is usually limited to towns like Kaza and Keylong. Download offline maps first."},
        {"name": "Altitude sickness", "score": altitude, "level": level(altitude),
         "message": (f"Your highest known point is {max_alt:,} m. Climb gradually, drink water, and descend if headaches or nausea worsen."
                     if max_alt else "No altitude data for your places. Treat anything above 2,500 m with care.")},
    ]

    # Budget: food * travellers * days + stay * rooms * days (two travellers share a room)
    n = clamp(int(travellers), 1, 20)
    d = clamp(int(days if days else total_days), 1, 40)
    rooms = math.ceil(n / 2)

    def estimate(t):
        food_rate, stay_rate = TIER_RATES[t]
        food, stay = food_rate * n * d, stay_rate * rooms * d
        return {"food": food, "stay": stay, "total": food + stay, "per_head": round_half_up((food + stay) / n)}

    return {
        "season": season, "season_months": months, "fallback": fallback,
        "places": places,
        "summary": {"days": total_days, "places": len(places), "trek_km": km, "max_altitude_m": max_alt},
        "season_check": {"status": status, "message": msg},
        "hazards": hazards,
        "place_notes": [place_note(p) for p in places if p["type"] != "trail"],
        "budget": {"travellers": n, "days": d, "tier": tier, "rooms": rooms, **estimate(tier),
                   "all_tiers": {t: estimate(t) for t in TIER_RATES}},
        "rates": {t: list(r) for t, r in TIER_RATES.items()},
    }
