import os
import yaml
import click
import asyncio
from pprint import pprint
from telethon import TelegramClient
from google import genai

from structured_output import structured_analysis, COMBINED_PROMPT


def parse_message_url(url):
    url = url.split('?')[0]  # remove any '?single' at the end
    parts = url.split('/')
    chat_id = parts[-2]
    message_id = int(parts[-1])
    return chat_id, message_id


@click.command()
@click.option('--post', required=True, help='Telegram post URL')
@click.option('--region', required=True, help='Region of interest')
@click.option('--languages', required=True, help='Lanugages of the posts')
def main(post, region, languages):
    asyncio.run(analyze_post(post, region, languages))


async def analyze_post(post: str, region: str, languages: str):
    """
    Get analysis for a given Telegram post URL.
    Args:
        post (str): Telegram post URL.
        region (str): Region of interest
        languages (str): languages of the posts
    """
    # Extract account name and message ID from the post URL
    chat_id, message_id = parse_message_url(post)

    # Initialize Telegram client
    with open("../../config.yaml") as f:
        config = yaml.safe_load(f)
        API_ID = config['secret_keys']['telethon']['api_id']
        API_HASH = config['secret_keys']['telethon']['api_hash']
        PHONE_NUMBER = config['secret_keys']['telethon']['phone']

    client = TelegramClient('tfa-gemini', API_ID, API_HASH)

    async with client:
        await client.start(PHONE_NUMBER)

        try:
            message = await client.get_messages(chat_id, ids=message_id)

        except Exception as e:
            print(f"Error access to {post}: {e}")

    print(f"Original text: {message.text}")

    config_path = os.path.join(os.path.dirname(__file__), '../../config.yaml')
    GOOGLE_API_KEY = yaml.safe_load(open(config_path))['secret_keys']['google']['api_key']
    client_genai = genai.Client(api_key=GOOGLE_API_KEY)

    result = structured_analysis(client_genai, message.text, COMBINED_PROMPT, region, languages)
    pprint(result)


if __name__ == '__main__':
    main()

# uv run analyze_post.py --post https://t.me/PalpostN/430141 --region "the Middle East (mainly, Gaza, Israel and West Bank)" --languages "Arabic, Hebrew, or English"
# Expected output: 
# Original text: **طيران الاحتلال ينفذ غارة جنوب شرق خانيونس جنوب قطاع غزة.**
# {'geolocations': [{'latitude': 31.342,
#                    'location_name': 'Khan Yunis',
#                    'longitude': 34.306}],
#  'sentiment': {'negative': 0.7, 'neutral': 0.3, 'positive': 0.0},
#  'translation': 'The occupation aircraft is carrying out a raid southeast of '
#                 'Khan Yunis, south of the Gaza Strip.'}