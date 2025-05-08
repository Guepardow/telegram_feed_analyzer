import yaml
import click
import asyncio
from pprint import pprint
from telethon import TelegramClient

from translation import translate_with_googletrans
from geolocation import load_model_geolocation, get_location_name, get_coordinates
from sentiment_analysis import load_model_sentiment, get_sentiment


def parse_message_url(url):
    url = url.split('?')[0]  # remove any '?single' at the end
    parts = url.split('/')
    chat_id = parts[-2]
    message_id = int(parts[-1])
    return chat_id, message_id


@click.command()
@click.option('--post', required=True, help='Telegram post URL')
def main(post):
    asyncio.run(analyze_post(post))


async def analyze_post(post: str):
    """
    Get analysis for a given Telegram post URL.
    Args:
        post (str): Telegram post URL.
    """
    # Extract account name and message ID from the post URL
    chat_id, message_id = parse_message_url(post)

    # Initialize Telegram client
    with open("../../config.yaml") as f:
        config = yaml.safe_load(f)
        API_ID = config['secret_keys']['telethon']['api_id']
        API_HASH = config['secret_keys']['telethon']['api_hash']
        PHONE_NUMBER = config['secret_keys']['telethon']['phone']

    client = TelegramClient('tfa-baseline', API_ID, API_HASH)

    async with client:
        await client.start(PHONE_NUMBER)

        try:
            message = await client.get_messages(chat_id, ids=message_id)

        except Exception as e:
            print(f"Error access to {post}: {e}")

    print(f"Original text: {message.text}")

    # Translation
    translated_text = await translate_with_googletrans(message.text)

    # Geolocation
    model_geolocation = load_model_geolocation()
    locations = get_location_name(translated_text, model_geolocation)
    coordinates = [get_coordinates(loc) for loc in locations]

    # Sentiment Analysis
    tokenizer_sentiment, model_sentiment = load_model_sentiment()
    sentiment = get_sentiment(translated_text, tokenizer_sentiment, model_sentiment)

    pprint({'geolocations': [{'location_name': loc, 'latitude': lat, 'longitude': lon} for loc, (lat, lon) in zip(locations, coordinates)], 
            'sentiment': sentiment, 'translation': translated_text, })


if __name__ == '__main__':
    main()

# uv run analyze_post.py --post https://t.me/PalpostN/430141

# Expected output : 
# {'geolocations': [{'latitude': 31.3443293,
#                    'location_name': 'Khan Yunis',
#                    'longitude': 34.3095897},
#                   {'latitude': -37.7137478,
#                    'location_name': 'Gaza Strip',
#                    'longitude': 145.0748898}],
#  'sentiment': {'negative': 0.401, 'neutral': 0.589, 'positive': 0.009},
#  'translation': '** The occupation aircraft is implementing a raid southeast '
#                 'of Khan Yunis, south of the Gaza Strip. **'}