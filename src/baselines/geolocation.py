from typing import Optional
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline


def load_model_geolocation():   
    """
    Load the model and tokenizer for geolocation.
    Returns:
        model: The loaded model.
        tokenizer: The loaded tokenizer.
    """
    # Name Entity Recognition
    MODEL_NAME = "Davlan/distilbert-base-multilingual-cased-ner-hrl"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForTokenClassification.from_pretrained(MODEL_NAME)

    return tokenizer, model

def get_location_name(text: str, model, tokenizer) -> list[str]:

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