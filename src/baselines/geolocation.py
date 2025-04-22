from typing import Optional
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

def get_location_name(text: str) -> list[str]:

    # Name Entity Recognition
    MODEL_NAME = "Davlan/distilbert-base-multilingual-cased-ner-hrl"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)
    model = pipeline("ner", model=model, tokenizer=tokenizer, aggregation_strategy="max")

    results = model(text)

    return(list(set([d['word'] for d in results if d['entity_group'] == 'LOC'])))


def get_coordinates(location_name: str) -> tuple[Optional[float], Optional[float]]:
    """
    Get coordinates for a given location name using Nominatim geocoder.
    Args:
        location_name (str): Name of the location to geocode.
    """
    geolocator = Nominatim(user_agent="telegram-feed-analyzer")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    geolocation = geocode(location_name)
    if geolocation is None:
        return (None, None)
    lat, lng = geolocation.latitude, geolocation.longitude
    return (lat, lng)


text = '**للمرة الثانية خلال أسابيع... الاحتلال يهدم منزلين في طوبا الزنغرية بالداخل الفلسطيني المحتل، صباح اليوم**'
locations = get_location_name(text)
print(locations)

for loc in locations:
    print(get_coordinates(loc))

print(get_coordinates("Tuba Al -Zangaria"))
print(get_coordinates("Tuba Zangariyya"))
print(get_coordinates("טובא זנגרייה"))
