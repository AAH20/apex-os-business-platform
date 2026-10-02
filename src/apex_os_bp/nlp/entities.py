"""Named entity extraction using pattern matching and heuristics."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class EntityType(str, Enum):
    """Types of entities that can be extracted."""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    TIME = "time"
    MONEY = "money"
    PERCENT = "percent"
    EMAIL = "email"
    URL = "url"
    PHONE = "phone"
    HASHTAG = "hashtag"
    MENTION = "mention"
    CURRENCY = "currency"
    NUMBER = "number"


@dataclass
class Entity:
    """An extracted entity."""

    text: str
    type: EntityType
    start: int = 0
    end: int = 0
    confidence: float = 1.0


# Common name prefixes/titles
_TITLES = {
    "mr", "mrs", "ms", "miss", "dr", "prof", "sir", "madam", "lord", "lady",
    "captain", "major", "colonel", "general", "judge", "senator", "representative",
    "president", "ceo", "cfo", "cto", "coo", "vp", "director", "manager",
}

# Common organization suffixes
_ORG_SUFFIXES = {
    "inc", "corp", "corporation", "llc", "ltd", "limited", "plc", "co",
    "company", "group", "partners", "associates", "consulting", "solutions",
    "technologies", "systems", "services", "enterprises", "industries",
    "labs", "studio", "agency", "foundation", "institute", "association",
    "organization", "university", "college", "school", "hospital", "bank",
    "capital", "ventures", "holdings", "partners",
}

# Common location indicators
_LOCATION_WORDS = {
    "street", "st", "avenue", "ave", "road", "rd", "boulevard", "blvd",
    "lane", "ln", "drive", "dr", "court", "ct", "way", "place", "pl",
    "square", "sq", "circle", "cir", "trail", "trl", "parkway", "pkwy",
    "highway", "hwy", "freeway", "fwy", "expressway", "expy", "turnpike",
    "terrace", "ter", "loop", "run", "path", "pike", "alley", "aly",
}

# Country and major city names for location detection
_COUNTRIES = {
    "afghanistan", "albania", "algeria", "andorra", "angola", "argentina",
    "armenia", "australia", "austria", "azerbaijan", "bahamas", "bahrain",
    "bangladesh", "barbados", "belarus", "belgium", "belize", "benin",
    "bhutan", "bolivia", "bosnia", "botswana", "brazil", "brunei", "bulgaria",
    "burkina", "burundi", "cambodia", "cameroon", "canada", "chad", "chile",
    "china", "colombia", "comoros", "congo", "costa", "croatia", "cuba",
    "cyprus", "czech", "denmark", "djibouti", "dominica", "dominican",
    "ecuador", "egypt", "salvador", "eritrea", "estonia", "ethiopia",
    "fiji", "finland", "france", "gabon", "gambia", "georgia", "germany",
    "ghana", "greece", "grenada", "guatemala", "guinea", "guyana", "haiti",
    "honduras", "hungary", "iceland", "india", "indonesia", "iran", "iraq",
    "ireland", "israel", "italy", "jamaica", "japan", "jordan", "kazakhstan",
    "kenya", "kiribati", "kosovo", "kuwait", "kyrgyzstan", "laos", "latvia",
    "lebanon", "lesotho", "liberia", "libya", "liechtenstein", "lithuania",
    "luxembourg", "madagascar", "malawi", "malaysia", "maldives", "mali",
    "malta", "marshall", "mauritania", "mauritius", "mexico", "micronesia",
    "moldova", "monaco", "mongolia", "montenegro", "morocco", "mozambique",
    "myanmar", "namibia", "nauru", "nepal", "netherlands", "zealand",
    "nicaragua", "niger", "nigeria", "korea", "norway", "oman", "pakistan",
    "palau", "palestine", "panama", "papua", "paraguay", "peru", "philippines",
    "poland", "portugal", "qatar", "romania", "russia", "rwanda", "samoa",
    "marino", "príncipe", "arabia", "senegal", "serbia", "seychelles",
    "singapore", "slovakia", "slovenia", "solomon", "somalia", "africa",
    "spain", "lanka", "sudan", "suriname", "swaziland", "sweden",
    "switzerland", "syria", "taiwan", "tajikistan", "tanzania", "thailand",
    "timor", "togo", "tonga", "trinidad", "tunisia", "turkey", "turkmenistan",
    "tuvalu", "uganda", "ukraine", "emirates", "britain", "america",
    "uruguay", "uzbekistan", "vanuatu", "venezuela", "vietnam", "yemen",
    "zambia", "zimbabwe",
}

_CITIES = {
    "london", "paris", "tokyo", "beijing", "shanghai", "moscow", "berlin",
    "madrid", "rome", "vienna", "amsterdam", "brussels", "dublin", "lisbon",
    "athens", "prague", "warsaw", "budapest", "stockholm", "oslo", "copenhagen",
    "helsinki", "reykjavik", "zurich", "geneva", "milan", "barcelona", "munich",
    "frankfurt", "hamburg", "cologne", "stuttgart", "dusseldorf", "leipzig",
    "dresden", "nuremberg", "hanover", "bremen", "bonn", "mainz", "mannheim",
    "karlsruhe", "freiburg", "heidelberg", "tubingen", "gottingen", "marburg",
    "giessen", "kiel", "flensburg", "rostock", "schwerin", "magdeburg",
    "potsdam", "erfurt", "weimar", "jena", "dessau", "cottbus", "brandenburg",
    "newyork", "losangeles", "chicago", "houston", "phoenix", "philadelphia",
    "sanantonio", "sandiego", "dallas", "sanfrancisco", "austin", "seattle",
    "denver", "boston", "atlanta", "miami", "orlando", "tampa", "portland",
    "vegas", "angeles", "york", "jersey", "changeles", "francisco", "diego",
    "antonio", "austin", "jose", "worth", "columbus", "charlotte", "indianapolis",
    "seattle", "denver", "washington", "boston", "el paso", "nashville",
    "detroit", "oklahoma", "portland", "las vegas", "louisville", "baltimore",
    "milwaukee", "albuquerque", "tucson", "fresno", "sacramento", "mesa",
    "kansas", "atlanta", "omaha", "colorado", "raleigh", "long beach",
    "virginia", "miami", "oakland", "minneapolis", "tulsa", "tampa", "arlington",
    "new orleans", "wichita", "cleveland", "bakersfield", "aurora", "anaheim",
    "honolulu", "santa", "riverside", "corpus", "lexington", "stockton",
    "pittsburgh", "saint paul", "anchorage", "cincinnati", "henderson",
    "greensboro", "plano", "newark", "lincoln", "orlando", "irvine", "toledo",
    "jersey", "chula", "durham", "laredo", "madison", "gilbert", "norfolk",
    "winston", "north", "richmond", "garland", "hialeah", "boise", "spokane",
    "baton rouge", "tacoma", "san bernardino", "modesto", "fontana", "santa clarita",
    "birmingham", "oxnard", "fayetteville", "rochester", "moreno valley",
    "glendale", "yonkers", "huntington", "aurora", "salt lake", "amarillo",
    "montgomery", "little rock", "akron", "shreveport", "augusta", "grand rapids",
    "mobile", "huntsville", "tallahassee", "grand prairie", "knoxville",
    "worcester", "newport", "brownsville", "overland park", "santa rosa",
    "chattanooga", "oceanside", "jackson", "fort lauderdale", "pasadena",
    "rockford", "joliet", "paterson", "naperville", "syracuse", "mesquite",
    "dayton", "savannah", "clarksville", "orange", "fullerton", "killeen",
    "frisco", "hampton", "mcallen", "warren", "bellevue", "west valley",
    "columbia", "new haven", "sterling", "miramar", "waco", "thousand oaks",
    "cedar rapids", "charleston", "visalia", "topeka", "elizabeth", "lafayette",
    "kent", "simi valley", "santa clara", "athens", "hartford", "victorville",
    "abilene", "norman", "vallejo", "berkeley", "round rock", "ann arbor",
    "fargo", "columbia", "allentown", "evansville", "beaumont", "odessa",
    "wilmington", "arvada", "independence", "provo", "murrieta", "el monte",
    "carlsbad", "temecula", "costa mesa", "miami gardens", "manchester",
    "westminster", "miami", "high point", "clearwater", "west jordan",
    "billings", "murrieta", "everett", "lowell", "centennial", "richmond",
    "ingleside", "broken arrow", "waterbury", "jacksonville", "las cruces",
    "sandy springs", "hillsboro", "greeley", "san buenaventura", "burbank",
    "green bay", "tyler", "davenport", "rialto", "los angeles", "san mateo",
    "lewisville", "south bend", "lakeland", "tyler", "allen", "surprise",
    "vancouver", "el cajon", "olathe", "topeka", "carrollton", "mcallen",
    "thornton", "roseville", "visalia", "coral springs", "stamford", "kent",
    "simi valley", "concord", "santa clara", "joliet", "jackson", "hattiesburg",
    "beaumont", "gainesville", "vallejo", "napa", "richmond", "avondale",
    "carlsbad", "san jacinto", "league city", "rochester hills", "daly city",
    "sierra vista", "redwood city", "tracy", "farmington hills", "charleston",
    "lewisville", "davenport", "murfreesboro", "high point", "san marcos",
    "columbia", "cedar rapids", "athens", "hartford", "victorville", "abilene",
    "norman", "vallejo", "berkeley", "round rock", "ann arbor", "fargo",
    "allentown", "evansville", "wilmington", "arvada", "independence",
    "provo", "el monte", "miami gardens", "westminster", "clearwater",
    "west jordan", "billings", "everett", "lowell", "centennial",
    "ingleside", "broken arrow", "waterbury", "las cruces", "sandy springs",
    "hillsboro", "greeley", "san buenaventura", "burbank", "tyler",
    "rialto", "lewisville", "south bend", "lakewood", "allen", "surprise",
    "el cajon", "olathe", "carrollton", "thornton", "roseville", "coral springs",
    "stamford", "concord", "hattiesburg", "gainesville", "avondale",
    "san jacinto", "league city", "rochester hills", "daly city",
    "sierra vista", "tracy", "farmington hills", "murfreesboro", "san marcos",
}

# US state names and abbreviations
_US_STATES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "hampshire", "jersey", "mexico", "york", "carolina", "dakota",
    "ohio", "oklahoma", "oregon", "pennsylvania", "rhode", "tennessee",
    "texas", "utah", "vermont", "virginia", "washington", "wisconsin",
    "wyoming",
}

_US_STATE_ABBREVS = {
    "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi",
    "id", "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi",
    "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc",
    "nd", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut",
    "vt", "va", "wa", "wv", "wi", "wy",
}

# Email pattern
_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)

# URL pattern
_URL_RE = re.compile(
    r"https?://[^\s<>\"{}|\\^`\[\]]+"
    r"|www\.[^\s<>\"{}|\\^`\[\]]+"
)

# Phone pattern (US/international)
_PHONE_RE = re.compile(
    r"(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"
    r"|\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,4}"
)

# Date patterns
_DATE_PATTERNS = [
    # MM/DD/YYYY or MM-DD-YYYY
    re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"),
    # YYYY/MM/DD or YYYY-MM-DD
    re.compile(r"\b(\d{4}[/-]\d{1,2}[/-]\d{1,2})\b"),
    # Month DD, YYYY
    re.compile(
        r"\b(January|February|March|April|May|June|July|August|September|"
        r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|"
        r"Nov|Dec)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",
        re.IGNORECASE,
    ),
    # DD Month YYYY
    re.compile(
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?"
        r"(January|February|March|April|May|June|July|August|September|"
        r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|"
        r"Nov|Dec),?\s+\d{4}\b",
        re.IGNORECASE,
    ),
]

# Time pattern
_TIME_RE = re.compile(
    r"\b(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[AaPp][Mm])?)\b"
)

# Money pattern
_MONEY_RE = re.compile(
    r"(?:[\$€£¥₹]\s?\d+(?:,\d{3})*(?:\.\d{2})?)"
    r"|(?:\d+(?:,\d{3})*(?:\.\d{2})?\s?(?:dollars?|euros?|pounds?|yen|rupees?|USD|EUR|GBP|JPY|INR))",
    re.IGNORECASE,
)

# Percent pattern
_PERCENT_RE = re.compile(r"\d+(?:\.\d+)?%|\d+(?:\.\d+)?\s+percent\b", re.IGNORECASE)

# Hashtag pattern
_HASHTAG_RE = re.compile(r"#\w+")

# Mention pattern
_MENTION_RE = re.compile(r"@\w+")

# Number pattern (cardinal and ordinal)
_NUMBER_RE = re.compile(
    r"\b\d+(?:,\d{3})*(?:\.\d+)?\b"
    r"|\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b",
    re.IGNORECASE,
)

# Capitalized word sequence (potential person/org name)
_CAPITALIZED_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b")

# Person name pattern: Title + Capitalized Word(s)
_PERSON_RE = re.compile(
    r"\b(Mr|Mrs|Ms|Miss|Dr|Prof|Sir|Madam|Lord|Lady|Captain|Major|Colonel|"
    r"General|Judge|Senator|Representative|President|CEO|CFO|CTO|COO|VP|"
    r"Director|Manager)\.?\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b"
)

# Organization pattern: Capitalized words + org suffix
_ORG_RE = re.compile(
    r"\b([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\s+"
    r"(?:Inc|Corp|Corporation|LLC|Ltd|Limited|PLC|Co|Company|Group|Partners|"
    r"Associates|Consulting|Solutions|Technologies|Systems|Services|"
    r"Enterprises|Industries|Labs|Studio|Agency|Foundation|Institute|"
    r"Association|Organization|University|College|School|Hospital|Bank|"
    r"Capital|Ventures|Holdings)\b\.?)"
)


@dataclass
class EntityExtractionResult:
    """Result of entity extraction."""

    entities: List[Entity] = field(default_factory=list)
    by_type: Dict[EntityType, List[Entity]] = field(default_factory=dict)

    def get_by_type(self, entity_type: EntityType) -> List[Entity]:
        """Get all entities of a specific type."""
        return self.by_type.get(entity_type, [])

    def count(self) -> int:
        """Total number of entities extracted."""
        return len(self.entities)


class EntityExtractor:
    """Extract named entities from text using pattern matching."""

    def __init__(self) -> None:
        self.titles = _TITLES
        self.org_suffixes = _ORG_SUFFIXES
        self.location_words = _LOCATION_WORDS
        self.countries = _COUNTRIES
        self.cities = _CITIES
        self.us_states = _US_STATES
        self.us_state_abbrevs = _US_STATE_ABBREVS

    def extract_emails(self, text: str) -> List[Entity]:
        """Extract email addresses."""
        entities = []
        for m in _EMAIL_RE.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.EMAIL,
                start=m.start(),
                end=m.end(),
                confidence=1.0,
            ))
        return entities

    def extract_urls(self, text: str) -> List[Entity]:
        """Extract URLs."""
        entities = []
        for m in _URL_RE.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.URL,
                start=m.start(),
                end=m.end(),
                confidence=1.0,
            ))
        return entities

    def extract_phones(self, text: str) -> List[Entity]:
        """Extract phone numbers."""
        entities = []
        for m in _PHONE_RE.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.PHONE,
                start=m.start(),
                end=m.end(),
                confidence=0.9,
            ))
        return entities

    def extract_dates(self, text: str) -> List[Entity]:
        """Extract dates."""
        entities = []
        for pattern in _DATE_PATTERNS:
            for m in pattern.finditer(text):
                entities.append(Entity(
                    text=m.group(),
                    type=EntityType.DATE,
                    start=m.start(),
                    end=m.end(),
                    confidence=0.9,
                ))
        return entities

    def extract_times(self, text: str) -> List[Entity]:
        """Extract times."""
        entities = []
        for m in _TIME_RE.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.TIME,
                start=m.start(),
                end=m.end(),
                confidence=0.9,
            ))
        return entities

    def extract_money(self, text: str) -> List[Entity]:
        """Extract monetary amounts."""
        entities = []
        for m in _MONEY_RE.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.MONEY,
                start=m.start(),
                end=m.end(),
                confidence=0.95,
            ))
        return entities

    def extract_percents(self, text: str) -> List[Entity]:
        """Extract percentages."""
        entities = []
        for m in _PERCENT_RE.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.PERCENT,
                start=m.start(),
                end=m.end(),
                confidence=0.95,
            ))
        return entities

    def extract_hashtags(self, text: str) -> List[Entity]:
        """Extract hashtags."""
        entities = []
        for m in _HASHTAG_RE.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.HASHTAG,
                start=m.start(),
                end=m.end(),
                confidence=1.0,
            ))
        return entities

    def extract_mentions(self, text: str) -> List[Entity]:
        """Extract @mentions."""
        entities = []
        for m in _MENTION_RE.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.MENTION,
                start=m.start(),
                end=m.end(),
                confidence=1.0,
            ))
        return entities

    def extract_numbers(self, text: str) -> List[Entity]:
        """Extract numbers (cardinal and ordinal)."""
        entities = []
        for m in _NUMBER_RE.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.NUMBER,
                start=m.start(),
                end=m.end(),
                confidence=0.8,
            ))
        return entities

    def extract_persons(self, text: str) -> List[Entity]:
        """Extract person names using title + capitalized pattern."""
        entities = []
        for m in _PERSON_RE.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.PERSON,
                start=m.start(),
                end=m.end(),
                confidence=0.85,
            ))

        # Also look for capitalized word sequences that might be names
        # (at least 2 words, not at start of sentence unless preceded by title)
        for m in _CAPITALIZED_RE.finditer(text):
            name = m.group()
            # Skip if it looks like a sentence start (single capitalized word
            # followed by lowercase)
            words = name.split()
            if len(words) >= 2:
                # Check if it's not already captured by the title pattern
                is_captured = any(
                    e.start <= m.start() < e.end for e in entities
                )
                if not is_captured:
                    entities.append(Entity(
                        text=name,
                        type=EntityType.PERSON,
                        start=m.start(),
                        end=m.end(),
                        confidence=0.6,
                    ))
        return entities

    def extract_organizations(self, text: str) -> List[Entity]:
        """Extract organization names."""
        entities = []
        for m in _ORG_RE.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.ORGANIZATION,
                start=m.start(),
                end=m.end(),
                confidence=0.85,
            ))
        return entities

    def extract_locations(self, text: str) -> List[Entity]:
        """Extract location names."""
        entities = []
        # Look for capitalized words that match known countries/cities/states
        for m in _CAPITALIZED_RE.finditer(text):
            name = m.group()
            name_lower = name.lower()
            words = name_lower.split()

            # Check if any word is a known location
            is_location = False
            for word in words:
                if (
                    word in self.countries
                    or word in self.cities
                    or word in self.us_states
                    or word in self.us_state_abbrevs
                ):
                    is_location = True
                    break

            if is_location:
                entities.append(Entity(
                    text=name,
                    type=EntityType.LOCATION,
                    start=m.start(),
                    end=m.end(),
                    confidence=0.75,
                ))

        # Look for address patterns
        address_pattern = re.compile(
            r"\b\d+\s+([A-Z][a-zA-Z]*(?:\s+[A-Z][a-zA-Z]*)*\s+"
            r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|"
            r"Drive|Dr|Court|Ct|Way|Place|Pl|Square|sq|Circle|Cir|"
            r"Trail|Trl|Parkway|Pkwy|Highway|Hwy|Terrace|Ter|Loop|Run|"
            r"Path|Pike|Alley|Aly))\b"
        )
        for m in address_pattern.finditer(text):
            entities.append(Entity(
                text=m.group(),
                type=EntityType.LOCATION,
                start=m.start(),
                end=m.end(),
                confidence=0.8,
            ))

        return entities

    def extract_all(self, text: str) -> EntityExtractionResult:
        """Extract all entity types from text."""
        all_entities: List[Entity] = []

        all_entities.extend(self.extract_emails(text))
        all_entities.extend(self.extract_urls(text))
        all_entities.extend(self.extract_phones(text))
        all_entities.extend(self.extract_dates(text))
        all_entities.extend(self.extract_times(text))
        all_entities.extend(self.extract_money(text))
        all_entities.extend(self.extract_percents(text))
        all_entities.extend(self.extract_hashtags(text))
        all_entities.extend(self.extract_mentions(text))
        all_entities.extend(self.extract_numbers(text))
        all_entities.extend(self.extract_persons(text))
        all_entities.extend(self.extract_organizations(text))
        all_entities.extend(self.extract_locations(text))

        # Remove overlapping entities (keep higher confidence)
        all_entities.sort(key=lambda e: (e.start, -e.confidence))
        filtered: List[Entity] = []
        last_end = -1
        for entity in all_entities:
            if entity.start >= last_end:
                filtered.append(entity)
                last_end = entity.end

        # Build by_type index
        by_type: Dict[EntityType, List[Entity]] = {}
        for entity in filtered:
            by_type.setdefault(entity.type, []).append(entity)

        return EntityExtractionResult(entities=filtered, by_type=by_type)
