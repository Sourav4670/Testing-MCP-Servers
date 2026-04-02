"""
travel_data.py – Static, deterministic knowledge base for the Travel Advisor MCP server.

All lookups are pure dictionary / list operations.  No external API calls,
no environment variables, no randomisation.  Every function with the same
inputs will always return the same output (referential transparency).

Design
------
City information is keyed by a *normalised* lowercase city name so lookups
are case-insensitive.  When an exact city is not found the code falls back
to a continent/hemisphere lookup based on country hints embedded in the
city name, and finally to a generic "unknown destination" profile.

Sections
--------
1. CITY_DATA          – per-city climate + safety + transport profiles
2. ATTRACTIVE_SPOTS   – top attractions keyed by city
3. ROUTE_DATA         – origin→destination route recommendations
4. MONTH_PROFILES     – seasonal crowd/weather summaries for each month
5. Helper functions   – normalise(), get_city_profile(), get_attractions(),
                        get_route_info(), get_month_profile()
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. CITY_DATA
#    Keys: normalised lowercase city name
#    Values: dict with keys –
#      climate     : short climate description
#      summer      : weather in boreal summer (Jun-Aug)
#      winter      : weather in boreal winter (Dec-Feb)
#      spring      : weather in Mar-May
#      autumn      : weather in Sep-Nov
#      safety      : general safety rating string
#      safety_tips : list[str]
#      transport   : dict { "air", "rail", "road", "sea" } availability flags
#      best_mode   : preferred long-distance transport mode
#      timezone    : UTC offset string  e.g. "UTC+5:30"
#      currency    : local currency code
#      language    : primary language
# ---------------------------------------------------------------------------

CITY_DATA: dict[str, dict] = {
    # ── North America ──────────────────────────────────────────────────────
    "new york": {
        "country": "USA",
        "climate": "Humid continental – hot summers, cold snowy winters",
        "summer": "Hot and humid, 28–35 °C, occasional thunderstorms",
        "winter": "Cold with snowfall, -5–5 °C, wind-chill common",
        "spring": "Mild and pleasant, 10–20 °C, rain possible",
        "autumn": "Crisp and colourful, 10–18 °C, ideal sightseeing",
        "safety": "Generally safe – exercise normal urban awareness",
        "safety_tips": [
            "Keep valuables out of sight on the subway",
            "Avoid isolated areas of Central Park after dark",
            "Use official yellow taxis or ride-share apps",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "flying for long-haul, Amtrak or bus for east-coast corridor",
        "timezone": "UTC-5 (EST) / UTC-4 (EDT)",
        "currency": "USD",
        "language": "English",
    },
    "los angeles": {
        "country": "USA",
        "climate": "Mediterranean – warm dry summers, mild wet winters",
        "summer": "Sunny and dry, 25–35 °C, marine layer mornings",
        "winter": "Mild, 12–20 °C, rain in Jan-Feb",
        "spring": "Warm and breezy, 18–25 °C",
        "autumn": "Warm and sunny, Santa Ana winds possible",
        "safety": "Moderate – traffic and some high-crime neighbourhoods",
        "safety_tips": [
            "Keep car doors locked; smash-and-grab is common",
            "Avoid Skid Row area",
            "Wildfires possible Sep-Nov; check CAL FIRE alerts",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "flying; renting a car once there is strongly advised",
        "timezone": "UTC-8 (PST) / UTC-7 (PDT)",
        "currency": "USD",
        "language": "English",
    },
    "chicago": {
        "country": "USA",
        "climate": "Humid continental – cold winters, warm summers, windy year-round",
        "summer": "Warm, 22–30 °C, occasional severe thunderstorms",
        "winter": "Very cold, -15–0 °C, heavy lake-effect snow",
        "spring": "Variable, 5–18 °C, tornado risk Apr-May",
        "autumn": "Mild and colourful, 8–18 °C",
        "safety": "Mixed – tourist areas safe; some south/west-side neighbourhoods high-crime",
        "safety_tips": [
            "Stay on the Magnificent Mile and tourist zones at night",
            "The 'L' train is safe during the day; exercise caution late at night",
            "Dress in warm layers Nov-Mar; wind-chill can be extreme",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": False},
        "best_mode": "flying; Amtrak for Midwest travel",
        "timezone": "UTC-6 (CST) / UTC-5 (CDT)",
        "currency": "USD",
        "language": "English",
    },
    # ── Europe ────────────────────────────────────────────────────────────
    "london": {
        "country": "UK",
        "climate": "Oceanic – mild and frequently overcast year-round",
        "summer": "Mild, 18–25 °C, rain possible; occasional heat waves",
        "winter": "Cold and grey, 3–10 °C, fog and drizzle",
        "spring": "Cool and showery, 10–17 °C",
        "autumn": "Mild with rain increasing, 10–18 °C",
        "safety": "Very safe – occasional street crime in busy zones",
        "safety_tips": [
            "Beware pickpockets on the Tube especially at rush hour",
            "Avoid unlicensed minicabs; use black cabs or Uber",
            "Tap & Go on the Oyster card for all public transport",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "Eurostar rail for Paris/Brussels; flying for further destinations",
        "timezone": "UTC+0 (GMT) / UTC+1 (BST)",
        "currency": "GBP",
        "language": "English",
    },
    "paris": {
        "country": "France",
        "climate": "Oceanic – warm summers, cool winters",
        "summer": "Warm, 20–28 °C; heat waves possible in Jul-Aug",
        "winter": "Cold, 2–8 °C, occasional frost",
        "spring": "Pleasant, 12–20 °C",
        "autumn": "Mild, 10–18 °C, increasing rain",
        "safety": "Generally safe – pickpockets near major tourist sites",
        "safety_tips": [
            "Guard against pickpockets at the Eiffel Tower and on the Métro",
            "Avoid unlit side streets late at night around Gare du Nord",
            "Validate your Métro ticket before each journey",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": False},
        "best_mode": "TGV high-speed rail for most European cities; flying for beyond",
        "timezone": "UTC+1 (CET) / UTC+2 (CEST)",
        "currency": "EUR",
        "language": "French",
    },
    "rome": {
        "country": "Italy",
        "climate": "Mediterranean – hot dry summers, mild wet winters",
        "summer": "Hot, 28–35 °C, very dry; peak tourist season",
        "winter": "Mild, 5–13 °C, some rain",
        "spring": "Warm and pleasant, 15–22 °C – best season",
        "autumn": "Warm, 15–22 °C; occasional heavy downpours",
        "safety": "Generally safe – scams and pickpockets near tourist sites",
        "safety_tips": [
            "Carry only a day's cash; leave passports in hotel safe",
            "Beware of overcharging at tourist-trap cafes near monuments",
            "Validate train and bus tickets before boarding",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "High-speed Frecciarossa rail within Italy; flying internationally",
        "timezone": "UTC+1 (CET) / UTC+2 (CEST)",
        "currency": "EUR",
        "language": "Italian",
    },
    "berlin": {
        "country": "Germany",
        "climate": "Humid continental – warm summers, cold winters",
        "summer": "Warm, 20–28 °C, thunderstorms possible",
        "winter": "Cold, -3–3 °C, grey and damp",
        "spring": "Cool and fresh, 8–18 °C",
        "autumn": "Mild, 8–16 °C",
        "safety": "Very safe for tourists",
        "safety_tips": [
            "Validate your U-Bahn/S-Bahn ticket – inspectors fine without mercy",
            "Cycling is popular; watch for cycle lanes when walking",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": False},
        "best_mode": "Deutsche Bahn ICE rail within Germany and neighbouring countries",
        "timezone": "UTC+1 (CET) / UTC+2 (CEST)",
        "currency": "EUR",
        "language": "German",
    },
    "amsterdam": {
        "country": "Netherlands",
        "climate": "Oceanic – mild and wet year-round",
        "summer": "Mild, 17–22 °C, some rain",
        "winter": "Cold, 1–6 °C, can be grey for weeks",
        "spring": "Cool and tulip season, 8–16 °C",
        "autumn": "Mild and rainy, 9–15 °C",
        "safety": "Very safe – watch for bicycles",
        "safety_tips": [
            "Stay off cycle lanes – cyclists have absolute right of way",
            "Lock rental bikes with both locks provided",
            "Red Light District is safe but note street photography rules",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "Thalys/Eurostar for UK/France; ICE for Germany",
        "timezone": "UTC+1 (CET) / UTC+2 (CEST)",
        "currency": "EUR",
        "language": "Dutch",
    },
    # ── Asia ──────────────────────────────────────────────────────────────
    "tokyo": {
        "country": "Japan",
        "climate": "Humid subtropical – four distinct seasons",
        "summer": "Hot and humid, 28–35 °C, typhoon risk Jul-Sep",
        "winter": "Cold but dry, 2–10 °C",
        "spring": "Cherry blossom, 10–18 °C – very crowded",
        "autumn": "Pleasant, 12–22 °C – second-best season",
        "safety": "One of the safest major cities in the world",
        "safety_tips": [
            "Keep quiet on public transport – talking loudly is considered rude",
            "IC card (Suica/Pasmo) makes trains and convenience stores seamless",
            "Carry cash – many small shops and shrines don't accept cards",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "Shinkansen bullet train for domestic; flying for international",
        "timezone": "UTC+9 (JST)",
        "currency": "JPY",
        "language": "Japanese",
    },
    "singapore": {
        "country": "Singapore",
        "climate": "Tropical rainforest – hot and humid year-round, no dry season",
        "summer": "30–33 °C, afternoon thunderstorms almost daily",
        "winter": "28–32 °C, northeast monsoon Dec-Mar",
        "spring": "30–33 °C, inter-monsoon rains",
        "autumn": "29–33 °C, southwest monsoon Jun-Sep",
        "safety": "Extremely safe – strict laws and enforcement",
        "safety_tips": [
            "No chewing gum, no littering, no jaywalking – fines are large",
            "Air quality can drop during haze season (Aug-Oct)",
            "MRT and buses cover the island comprehensively",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "Flying for international; MRT within the city",
        "timezone": "UTC+8 (SGT)",
        "currency": "SGD",
        "language": "English (official), Mandarin, Malay, Tamil",
    },
    "dubai": {
        "country": "UAE",
        "climate": "Hot desert – extremely hot summers, pleasant winters",
        "summer": "Extremely hot, 38–47 °C, high humidity near coast",
        "winter": "Warm and pleasant, 18–26 °C – peak tourist season",
        "spring": "Hot, 28–38 °C",
        "autumn": "Still hot, 32–40 °C",
        "safety": "Very safe for tourists – low crime",
        "safety_tips": [
            "Dress modestly in malls, souks, and public areas",
            "Public display of affection may draw police attention",
            "Alcohol only in licenced hotels and restaurants",
            "Avoid outdoor activity midday in summer; heat stroke risk",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "Flying is hub of global connections; Dubai Metro within city",
        "timezone": "UTC+4 (GST)",
        "currency": "AED",
        "language": "Arabic (English widely spoken)",
    },
    "mumbai": {
        "country": "India",
        "climate": "Tropical wet and dry – hot and humid; torrential monsoon Jun-Sep",
        "summer": "Hot, 32–38 °C, humid",
        "winter": "Pleasant, 18–28 °C – best time to visit",
        "spring": "Hot and dry, 30–40 °C",
        "autumn": "Post-monsoon, 25–32 °C, pleasant",
        "safety": "Moderate – follow urban safety norms",
        "safety_tips": [
            "Avoid displaying expensive jewellery in crowded areas",
            "Use pre-booked cabs or official auto-rickshaws with meters",
            "Monsoon flooding can disrupt travel Jun-Sep; check bulletins",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "Flying for long routes; Vande Bharat/Rajdhani trains for domestic",
        "timezone": "UTC+5:30 (IST)",
        "currency": "INR",
        "language": "Hindi, Marathi, English",
    },
    "delhi": {
        "country": "India",
        "climate": "Semi-arid – very hot summers, mild winters, monsoon Jul-Sep",
        "summer": "Very hot, 38–45 °C; dust storms possible",
        "winter": "Cool, 5–18 °C; dense fog Dec-Jan",
        "spring": "Pleasant, 20–33 °C; rises quickly to summer",
        "autumn": "Pleasant post-monsoon, 22–33 °C",
        "safety": "Exercise caution – petty crime and traffic are concerns",
        "safety_tips": [
            "Use Delhi Metro – reliable, cheap, and safe",
            "Avoid accepting unsolicited help from strangers at the airport",
            "Book accommodation in central areas (Connaught Place, South Delhi)",
            "Air quality can be severe Oct-Feb; carry a good N95 mask",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": False},
        "best_mode": "Flying for international; Rajdhani/Shatabdi trains for domestic",
        "timezone": "UTC+5:30 (IST)",
        "currency": "INR",
        "language": "Hindi, English",
    },
    "beijing": {
        "country": "China",
        "climate": "Humid continental – cold dry winters, hot humid summers",
        "summer": "Hot, 28–35 °C, heavy rain possible",
        "winter": "Cold and dry, -10–2 °C",
        "spring": "Sandstorms possible Mar-May, warming up",
        "autumn": "Crisp, 10–20 °C – best season",
        "safety": "Generally safe for tourists",
        "safety_tips": [
            "Install a VPN before arrival if you need Google/WhatsApp",
            "Carry some cash – not all places accept foreign cards",
            "Air quality varies; check AQI app daily",
            "Register at hotel within 24 hours (legally required)",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": False},
        "best_mode": "Fuxing high-speed rail for domestic; flying internationally",
        "timezone": "UTC+8 (CST)",
        "currency": "CNY",
        "language": "Mandarin",
    },
    "bangkok": {
        "country": "Thailand",
        "climate": "Tropical – hot year-round, strong monsoon May-Oct",
        "summer": "Hot and wet, 30–36 °C, heavy afternoon rain",
        "winter": "Hot and dry, 25–33 °C – peak season",
        "spring": "Hot and humid, 32–38 °C – hottest period",
        "autumn": "Wet, 28–33 °C, flooding risk",
        "safety": "Generally safe – scams and traffic are main concerns",
        "safety_tips": [
            "Avoid tuk-tuk drivers who offer 'free tours' (always a gem shop detour)",
            "Dress modestly at temples – shoulders and knees covered",
            "Songkran (April) – expect water fights city-wide",
            "Keep valuables close on crowded BTS/MRT trains",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "BTS Skytrain/MRT within Bangkok; flying for southern islands",
        "timezone": "UTC+7 (ICT)",
        "currency": "THB",
        "language": "Thai",
    },
    # ── Oceania ───────────────────────────────────────────────────────────
    "sydney": {
        "country": "Australia",
        "climate": "Humid subtropical – warm summers, mild winters",
        "summer": "Hot, 25–35 °C, bushfire risk, UV very high",
        "winter": "Mild, 8–17 °C, mostly sunny",
        "spring": "Warm and wildflower season, 15–24 °C",
        "autumn": "Mild and dry, 15–22 °C",
        "safety": "Very safe",
        "safety_tips": [
            "Apply SPF 50+ sunscreen – UV index regularly extreme",
            "Swim between the flags at beaches (rip currents are serious)",
            "Tap water is safe and of high quality everywhere",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "Flying between major Australian cities; ferry/train within Sydney",
        "timezone": "UTC+10 (AEST) / UTC+11 (AEDT)",
        "currency": "AUD",
        "language": "English",
    },
    # ── South America ──────────────────────────────────────────────────────
    "rio de janeiro": {
        "country": "Brazil",
        "climate": "Tropical – hot year-round, rainy season Nov-Mar",
        "summer": "Hot, 28–38 °C, heavy afternoon rain and landslide risk",
        "winter": "Warm, 18–25 °C – best time to visit",
        "spring": "Warming up, 22–30 °C",
        "autumn": "Hot, 24–32 °C, rains easing",
        "safety": "Use caution – petty theft, mugging in certain areas",
        "safety_tips": [
            "Avoid wearing flashy jewellery or visible expensive electronics",
            "Use app-based taxis (99/Uber) rather than street cabs",
            "Stick to well-lit touristy areas at night (Ipanema, Leblon)",
            "Leave passports in hotel safe; carry a photocopy",
        ],
        "transport": {"air": True, "rail": False, "road": True, "sea": True},
        "best_mode": "Flying domestic; Buses for intercity in South America",
        "timezone": "UTC-3 (BRT)",
        "currency": "BRL",
        "language": "Portuguese",
    },
    # ── Africa ─────────────────────────────────────────────────────────────
    "cape town": {
        "country": "South Africa",
        "climate": "Mediterranean – hot dry summers, wet mild winters",
        "summer": "Hot, 25–33 °C, strong southeaster wind 'Cape Doctor'",
        "winter": "Wet and cool, 7–18 °C – best for game drives",
        "spring": "Pleasant, 16–24 °C, wildflowers Sep-Oct",
        "autumn": "Warm, 18–25 °C",
        "safety": "Exercise caution – car theft and mugging are risks",
        "safety_tips": [
            "Keep car doors locked and valuables out of sight",
            "Avoid Khayelitsha and certain CBD areas after dark",
            "Table Mountain hikes – go in groups, stay on marked paths",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": True},
        "best_mode": "Flying between South African cities; renting a car locally",
        "timezone": "UTC+2 (SAST)",
        "currency": "ZAR",
        "language": "Afrikaans, English, Xhosa (11 official)",
    },
    "nairobi": {
        "country": "Kenya",
        "climate": "Subtropical highland – mild year-round, two rainy seasons",
        "summer": "Dry, 20–28 °C (Jun-Sep)",
        "winter": "Short rains Oct-Dec, 16–24 °C",
        "spring": "Long rains Mar-May, 18–24 °C",
        "autumn": "Cool dry season, 16–24 °C",
        "safety": "Moderate – petty crime; check travel advisories",
        "safety_tips": [
            "Use reputable safari operators and licensed taxis",
            "Avoid walking alone after dark in the CBD",
            "Malaria prophylaxis recommended for rural areas",
            "Yellow fever vaccination recommended",
        ],
        "transport": {"air": True, "rail": True, "road": True, "sea": False},
        "best_mode": "Flying within East Africa; SGR train to Mombasa",
        "timezone": "UTC+3 (EAT)",
        "currency": "KES",
        "language": "Swahili, English",
    },
}

# ---------------------------------------------------------------------------
# 2. ATTRACTIVE_SPOTS – top 5 attractions per city
# ---------------------------------------------------------------------------

ATTRACTIONS: dict[str, list[str]] = {
    "new york": [
        "Statue of Liberty & Ellis Island – ferry from Battery Park",
        "Central Park – 843-acre urban park; great for cycling",
        "Metropolitan Museum of Art (The Met) – world-class collection",
        "Times Square & Broadway – evening shows highly recommended",
        "The High Line – elevated linear park with Hudson views",
    ],
    "los angeles": [
        "Griffith Observatory – free, stunning downtown skyline views",
        "Getty Center – world-class art, free entry (parking fee only)",
        "Venice Beach Boardwalk – street performers, murals, sunset",
        "Hollywood Walk of Fame & Chinese Theatre",
        "Santa Monica Pier & Pacific Park",
    ],
    "chicago": [
        "Millennium Park & Cloud Gate ('The Bean')",
        "Art Institute of Chicago – one of the finest art museums in the US",
        "Navy Pier – lakefront entertainment complex",
        "Willis Tower Skydeck – glasss ledge 103 floors up",
        "Chicago Riverwalk – architecture boat tours from here",
    ],
    "london": [
        "British Museum – free, 8 million objects spanning human history",
        "Tower of London & Tower Bridge",
        "National Gallery, Trafalgar Square – free",
        "Buckingham Palace & St James's Park",
        "Borough Market – London's oldest food market",
    ],
    "paris": [
        "Eiffel Tower – book timed entry in advance",
        "Louvre Museum – home of the Mona Lisa; allow a full day",
        "Musée d'Orsay – Impressionist masterpieces",
        "Notre-Dame Cathedral (under restoration; exterior viewing)",
        "Montmartre & Sacré-Cœur – bohemian hilltop neighbourhood",
    ],
    "rome": [
        "Colosseum & Roman Forum – book tickets online to skip queues",
        "Vatican Museums, Sistine Chapel & St Peter's Basilica",
        "Trevi Fountain – throw a coin for good luck",
        "Borghese Gallery – Bernini sculptures; advance booking essential",
        "Trastevere neighbourhood – authentic Roman dining and cobblestones",
    ],
    "berlin": [
        "Brandenburg Gate & Reichstag (glass dome – free, book online)",
        "Berlin Wall Memorial & East Side Gallery",
        "Museum Island – 5 world-class museums on one island",
        "Holocaust Memorial (Memorial to the Murdered Jews of Europe)",
        "Charlottenburg Palace & gardens",
    ],
    "amsterdam": [
        "Rijksmuseum – Rembrandt and Vermeer originals",
        "Van Gogh Museum – complete life's work chronologically",
        "Anne Frank House – book weeks in advance",
        "Canal boat tour – best overview of the city",
        "Vondelpark – relax with locals on a sunny day",
    ],
    "tokyo": [
        "Senso-ji Temple, Asakusa – Tokyo's oldest temple",
        "Shibuya Crossing & Scramble Square observation deck",
        "teamLab Borderless digital art museum",
        "Tsukiji Outer Market – best sushi breakfast in the world",
        "Harajuku Takeshita Street & Meiji Shrine",
    ],
    "singapore": [
        "Gardens by the Bay & Supertree Grove (free after dark for light show)",
        "Marina Bay Sands SkyPark observation deck",
        "Hawker centres – Maxwell, Lau Pa Sat (cheapest Michelin food on Earth)",
        "Singapore Botanic Gardens – UNESCO World Heritage Site, free",
        "Sentosa Island – Universal Studios, beaches, cable car",
    ],
    "dubai": [
        "Burj Khalifa 'At The Top' observation deck – book sunrise slot",
        "Dubai Mall & Dubai Fountain show (free, evenings)",
        "Old Dubai – Al Fahidi Historic District & Gold/Spice Souks",
        "Desert Safari with dune bashing and Bedouin dinner",
        "Palm Jumeirah & Atlantis Aquaventure",
    ],
    "mumbai": [
        "Gateway of India & Elephanta Caves (ferry across the harbour)",
        "Chhatrapati Shivaji Maharaj Terminus (CST) – UNESCO heritage station",
        "Juhu Beach & Girgaon Chowpatty – local street-food culture",
        "Dharavi Slum Tour – eye-opening eco, art & industry walks",
        "Bollywood studio tour, Film City",
    ],
    "delhi": [
        "Red Fort (Lal Qila) – UNESCO heritage Mughal citadel",
        "Humayun's Tomb – forerunner to the Taj Mahal",
        "Qutub Minar – world's tallest brick minaret",
        "India Gate & Rashtrapati Bhavan ceremonial boulevard",
        "Chandni Chowk – historic bazaar for street food and textiles",
    ],
    "beijing": [
        "Great Wall of China – Mutianyu section less crowded than Badaling",
        "Forbidden City (Palace Museum) – book tickets in advance",
        "Temple of Heaven & morning tai chi in the park",
        "Summer Palace – imperial lakeside gardens",
        "Tiananmen Square & National Museum of China (free)",
    ],
    "bangkok": [
        "Grand Palace & Wat Phra Kaew (Temple of the Emerald Buddha)",
        "Wat Arun (Temple of Dawn) – photo from the Chao Phraya",
        "Chatuchak Weekend Market – 15,000 stalls of everything",
        "Floating markets – Damnoen Saduak or Amphawa (day trip)",
        "Khao San Road – backpacker hub with rooftop bars",
    ],
    "sydney": [
        "Sydney Opera House – even if not seeing a show, take the guided tour",
        "Sydney Harbour Bridge – BridgeClimb for panoramic views",
        "Bondi Beach & Bondi to Coogee coastal walk",
        "Taronga Zoo – city skyline backdrop with native wildlife",
        "The Rocks & Circular Quay – oldest European settlement area",
    ],
    "rio de janeiro": [
        "Christ the Redeemer (Cristo Redentor) – take the cog train",
        "Sugarloaf Mountain (Pão de Açúcar) – cable car sunset",
        "Copacabana & Ipanema beaches",
        "Lapa Arches & Santa Teresa bohemian neighbourhood",
        "Tijuca National Forest – largest urban rainforest in the world",
    ],
    "cape town": [
        "Table Mountain – cable car or hike; check cloud conditions first",
        "Cape Point & Cape of Good Hope – dramatic peninsula scenery",
        "Robben Island – tour Nelson Mandela's former prison cell",
        "V&A Waterfront – restaurants, museums, boat trips",
        "Boulders Beach Penguin Colony (near Simon's Town)",
    ],
    "nairobi": [
        "Nairobi National Park – lions with city skyline backdrop",
        "David Sheldrick Elephant Orphanage – morning baby-elephant feeding",
        "Karen Blixen Museum – 'Out of Africa' farm on city outskirts",
        "Giraffe Centre – hand feed endangered Rothschild giraffes",
        "Maasai Market (varies by day) – crafts and jewellery",
    ],
}

# ---------------------------------------------------------------------------
# 3. MONTH_PROFILES – each month: crowd level, event highlights
# ---------------------------------------------------------------------------

MONTH_PROFILES: dict[int, dict] = {
    1:  {"name": "January",   "hemisphere_north": "winter",  "season": "off-peak in most of Europe/Asia; peak in Caribbean/Dubai"},
    2:  {"name": "February",  "hemisphere_north": "winter",  "season": "Carnival season (Rio/Venice); Chinese New Year travel surge"},
    3:  {"name": "March",     "hemisphere_north": "spring",  "season": "shoulder season begins; Tokyo cherry blossoms late-March"},
    4:  {"name": "April",     "hemisphere_north": "spring",  "season": "cherry blossom peak Tokyo; Easter crowds in Rome; holy week"},
    5:  {"name": "May",       "hemisphere_north": "spring",  "season": "ideal weather many destinations; Cannes Film Festival"},
    6:  {"name": "June",      "hemisphere_north": "summer",  "season": "school holidays begin; peak Europe crowds; monsoon starts South Asia"},
    7:  {"name": "July",      "hemisphere_north": "summer",  "season": "peak global tourism; book well in advance; highest prices"},
    8:  {"name": "August",    "hemisphere_north": "summer",  "season": "peak summer; European holiday exodus; typhoon risk East Asia"},
    9:  {"name": "September", "hemisphere_north": "autumn",  "season": "shoulder season; excellent weather, lower prices; Oktoberfest"},
    10: {"name": "October",   "hemisphere_north": "autumn",  "season": "ideal for many destinations; foliage peak N. America/Japan"},
    11: {"name": "November",  "hemisphere_north": "autumn",  "season": "off-peak begins Nth hemisphere; peak season Maldives/Thailand"},
    12: {"name": "December",  "hemisphere_north": "winter",  "season": "festive markets Europe; peak Australia/South Africa; expensive"},
}

# ---------------------------------------------------------------------------
# 4. ROUTE DATA – specific origin→destination insights
#    Key: frozenset({origin_normalised, destination_normalised})
#    (order-independent lookup so A→B == B→A have the same base facts)
# ---------------------------------------------------------------------------

ROUTE_DATA: dict[frozenset, dict] = {
    frozenset({"london", "paris"}): {
        "fastest_mode": "Eurostar train (2 h 16 min city-centre to city-centre)",
        "alternatives": "Budget airlines (EasyJet, Ryanair) if booked early",
        "distance_km": 450,
        "direct_flight_hours": 1.3,
        "note": "Eurostar is faster door-to-door than flying once airport time is counted",
    },
    frozenset({"new york", "london"}): {
        "fastest_mode": "Non-stop flight (7 h JFK–LHR, 6.5 h westbound)",
        "alternatives": "No practical surface alternative",
        "distance_km": 5_570,
        "direct_flight_hours": 7.0,
        "note": "Look for codeshare deals; Terminal 5 at LHR for BA; T1/T4 for others",
    },
    frozenset({"london", "new york"}): {  # same but explicit
        "fastest_mode": "Non-stop flight (7 h JFK–LHR, 6.5 h westbound)",
        "alternatives": "No practical surface alternative",
        "distance_km": 5_570,
        "direct_flight_hours": 7.0,
        "note": "Look for codeshare deals; Terminal 5 at LHR for BA; T1/T4 for others",
    },
    frozenset({"delhi", "mumbai"}): {
        "fastest_mode": "Flight (1 h 50 min)",
        "alternatives": "Rajdhani Express overnight train (16 h – scenic and economical)",
        "distance_km": 1_148,
        "direct_flight_hours": 1.8,
        "note": "Train is remarkably comfortable and a unique travel experience",
    },
    frozenset({"tokyo", "osaka"}): {
        "fastest_mode": "Nozomi Shinkansen (2 h 30 min)",
        "alternatives": "Hikari Shinkansen (3 h, JR Pass accepted); night bus (8 h, very cheap)",
        "distance_km": 508,
        "direct_flight_hours": 1.2,
        "note": "Flying is not recommended for this route – Shinkansen wins on convenience",
    },
    frozenset({"singapore", "bangkok"}): {
        "fastest_mode": "Flight (2 h 20 min)",
        "alternatives": "Eastern & Oriental Express luxury train (41 h)",
        "distance_km": 1_430,
        "direct_flight_hours": 2.4,
        "note": "Many low-cost options: AirAsia, Scoot, Jetstar",
    },
    frozenset({"sydney", "melbourne"}): {
        "fastest_mode": "Flight (1 h 25 min)",
        "alternatives": "XPT overnight train (10 h); Greyhound bus (9 h scenic)",
        "distance_km": 880,
        "direct_flight_hours": 1.4,
        "note": "Qantas/Jetstar shuttle every hour; most frequent route in Australia",
    },
    frozenset({"paris", "berlin"}): {
        "fastest_mode": "Flight (1 h 55 min)",
        "alternatives": "TGV/ICE via Frankfurt (8 h); EuroNight sleeper (13 h)",
        "distance_km": 1_050,
        "direct_flight_hours": 2.0,
        "note": "Night train makes scenic economic sense for budget and eco-conscious travellers",
    },
    frozenset({"beijing", "shanghai"}): {
        "fastest_mode": "Fuxing G-class high-speed rail (4 h 18 min)",
        "alternatives": "D-class express (6 h); overnight train (12 h); flight (2 h incl airport)",
        "distance_km": 1_318,
        "direct_flight_hours": 2.2,
        "note": "Rail is highly recommended – city-centre to city-centre, no airport hassle",
    },
    frozenset({"dubai", "mumbai"}): {
        "fastest_mode": "Flight (3 h)",
        "alternatives": "No sea line currently practical for tourists",
        "distance_km": 1_930,
        "direct_flight_hours": 3.0,
        "note": "Emirates and Air India have very frequent daily connections",
    },
}

# ---------------------------------------------------------------------------
# 5. Helper functions
# ---------------------------------------------------------------------------

def _normalise(name: str) -> str:
    """Lower-case and strip a city name for dict lookups."""
    return name.strip().lower()


def _season_from_month(month: int, city_key: str) -> str:
    """
    Derive the meteorological season descriptor for a city given a month number.

    Southern-hemisphere cities flip the season (Jun→summer, Dec→winter).
    """
    southern = {"sydney", "cape town", "rio de janeiro"}
    northern_season_map = {
        12: "winter", 1: "winter", 2: "winter",
        3:  "spring", 4: "spring", 5: "spring",
        6:  "summer", 7: "summer", 8: "summer",
        9:  "autumn", 10: "autumn", 11: "autumn",
    }
    flip = {"winter": "summer", "summer": "winter", "spring": "autumn", "autumn": "spring"}
    season = northern_season_map.get(month, "summer")
    if city_key in southern:
        season = flip[season]
    return season


def get_city_profile(city: str) -> dict:
    """
    Return the profile dict for *city*, falling back to a generic profile.

    Args:
        city: Raw city name from caller (any case).

    Returns:
        Profile dict (always non-None).
    """
    key = _normalise(city)
    if key in CITY_DATA:
        return CITY_DATA[key]
    # Partial-match fallback (e.g. "New York City" → "new york")
    for k in CITY_DATA:
        if k in key or key in k:
            return CITY_DATA[k]
    # Generic fallback
    return {
        "country": "Unknown",
        "climate": "Climate data not available for this destination",
        "summer": "Typically warm – verify locally",
        "winter": "Typically cool – verify locally",
        "spring": "Mild – verify locally",
        "autumn": "Moderate – verify locally",
        "safety": "Check your government's travel advisory before departure",
        "safety_tips": [
            "Register with your embassy on arrival for extended stays",
            "Keep digital copies of all travel documents",
            "Ensure travel insurance covers medical evacuation",
        ],
        "transport": {"air": True, "rail": False, "road": True, "sea": False},
        "best_mode": "Flying is likely the most practical option",
        "timezone": "Verify locally",
        "currency": "Verify locally",
        "language": "Verify locally",
    }


def get_attractions(city: str) -> list[str]:
    """Return the list of top attractions for *city* (fallback to generic list)."""
    key = _normalise(city)
    if key in ATTRACTIONS:
        return ATTRACTIONS[key]
    for k in ATTRACTIONS:
        if k in key or key in k:
            return ATTRACTIONS[k]
    return [
        "Visit the city's main historic centre or old town",
        "Explore the local central market for food and culture",
        "Check UNESCO World Heritage Sites in the region",
        "Take a guided walking tour on arrival to orientate",
        "Ask hotel concierge for current local events",
    ]


def get_route_info(origin: str, destination: str) -> dict | None:
    """
    Return route-specific advice if the city pair is in ROUTE_DATA, else None.
    """
    key = frozenset({_normalise(origin), _normalise(destination)})
    return ROUTE_DATA.get(key)


def get_month_profile(month: int) -> dict:
    """Return the month profile dict for *month* (1–12)."""
    return MONTH_PROFILES.get(month, MONTH_PROFILES[7])  # default to July


def get_weather_for_season(city: str, season: str) -> str:
    """Return the weather string for *city* in *season*."""
    profile = get_city_profile(city)
    return profile.get(season, profile.get("summer", "Warm conditions expected"))


def get_peak_off_peak(month: int, city: str) -> str:
    """
    Determine whether travel in *month* to *city* is peak, shoulder, or off-peak.

    Logic is deterministic: peak = Jun-Aug + Dec for most Northern cities;
    flipped for Southern-hemisphere cities.
    """
    key = _normalise(city)
    southern = {"sydney", "cape town", "rio de janeiro"}

    # Peak months per hemisphere
    peak_north   = {6, 7, 8, 12}
    off_peak_north = {1, 2, 11}
    peak_south   = {12, 1, 2, 7}  # southern summer + school hols
    off_peak_south = {5, 6, 9}

    if key in southern or (key not in CITY_DATA and month in peak_south):
        peak, off_peak = peak_south, off_peak_south
    else:
        peak, off_peak = peak_north, off_peak_north

    if month in peak:
        return "PEAK season – expect crowds and higher prices; book early"
    elif month in off_peak:
        return "OFF-PEAK season – fewer crowds and lower prices; excellent value"
    else:
        return "SHOULDER season – good balance of weather, crowds, and price"
