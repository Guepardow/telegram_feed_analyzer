import yaml
import click
import asyncio
from telethon import TelegramClient

from gemini.structured_output import structured_analysis, COMBINED_PROMPT
from baselines.translation import translate_with_googletrans
from baselines.geolocation import load_model_geolocation, get_location_name, get_coordinates
from baselines.sentiment_analysis import load_model_sentiment, get_sentiment


def parse_message_url(url):
    url = url.split('?')[0]  # remove any '?single' at the end
    parts = url.split('/')
    chat_id = parts[-2]
    message_id = int(parts[-1])
    return chat_id, message_id


@click.command()
@click.option('--post', required=True, help='Telegram post URL')
@click.option('--method', type=click.Choice(['gemini', 'baseline']), default='gemini', help='Method to use for analysis')
def main(post, method):
    asyncio.run(get_analysis(post, method))


async def get_analysis(post, method):
    """
    Get analysis for a given Telegram post URL using the specified method.
    Args:
        post (str): Telegram post URL.
        method (str): Method to use for analysis ('gemini' or 'baseline').
    """
    # Extract account name and message ID from the post URL
    chat_id, message_id = parse_message_url(post)

    # Initialize Telegram client
    with open("../config.yaml") as f:
        config = yaml.safe_load(f)
        API_ID = config['secret_keys']['telethon']['api_id']
        API_HASH = config['secret_keys']['telethon']['api_hash']
        PHONE_NUMBER = config['secret_keys']['telethon']['phone']

    client = TelegramClient('session_name', API_ID, API_HASH)

    async with client:
        await client.start(PHONE_NUMBER)

        try:
            message = await client.get_messages(chat_id, ids=message_id)

        except Exception as e:
            print(f"Error access to {post}: {e}")

    print(f"Original text: {message.text}")

    if method == 'gemini':
        result = structured_analysis(message.text, COMBINED_PROMPT)
        print(result)

    elif method == 'baseline':

        # Translation
        translated_text = await translate_with_googletrans(message.text)

        # Geolocation
        tokenizer_geolocation, model_geolocation = load_model_geolocation()
        locations = get_location_name(translated_text, model_geolocation, tokenizer_geolocation)
        coordinates = [get_coordinates(loc) for loc in locations]

        # Sentiment Analysis
        tokenizer_sentiment, model_sentiment = load_model_sentiment()
        sentiment = get_sentiment(translated_text, tokenizer_sentiment, model_sentiment)

        print({'translated_text': translated_text, 'locations': locations, 'coordinates': coordinates, 'sentiment': sentiment})


if __name__ == '__main__':
    main()

# uv run get_analysis.py --post https://t.me/PalpostN/430141 --method baseline
# uv run get_analysis.py --post https://t.me/PalpostN/430141 --method gemini