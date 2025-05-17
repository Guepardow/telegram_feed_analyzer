import os
import yaml
import json
import click
import asyncio
from google import genai
from loguru import logger
from zoneinfo import ZoneInfo
from telethon.sync import TelegramClient, events

from src.gemini.structured_output import structured_analysis, COMBINED_PROMPT


# Collect keys for Telegram and Gemini AI
with open("config.yaml") as file:
    config = yaml.safe_load(file)

    API_ID = config['secret_keys']['telegram']['api_id']
    API_HASH = config['secret_keys']['telegram']['api_hash']
    PHONE_NUMBER = config['secret_keys']['telegram']['phone']

    GOOGLE_API_KEY = config['secret_keys']['google']['api_key']

@click.command()
@click.option('--datamap', required=True, help="Name of the folder")
def main(datamap):
    asyncio.run(run(datamap))


async def run(datamap):
    # Collect information about the live
    with open(os.path.join('./data/datamaps/', datamap, 'datamap-config.yaml')) as file:
        datamap_config  = yaml.safe_load(file)

        REGION = datamap_config['map']['region']
        LANGUAGES = datamap_config['map']['languages']
        CHANNELS = datamap_config['telegram']
        TIMEZONE = datamap_config['date']['timezone']

    # Create a JSON file if it does not exist
    jsonl_path = os.path.join('./data/datamaps/', datamap, 'telegram_gemini.jsonl')
    if not os.path.exists(jsonl_path):
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            f.write('')

    client = TelegramClient('live', API_ID, API_HASH)
    logger.success("Connected to Telegram")

    client_genai = genai.Client(api_key=GOOGLE_API_KEY)
    logger.success("Connected to Google API")

    @client.on(events.NewMessage(chats=CHANNELS))
    async def handler(event):
        await new_message_handler(event, datamap, client_genai, COMBINED_PROMPT, REGION, LANGUAGES, TIMEZONE)

    await client.start()
    logger.info(f'Listening for new messages in {", ".join(CHANNELS)} ...')

    # Keep the script running
    await client.run_until_disconnected()


async def new_message_handler(event, datamap, client_genai, prompt, region, languages, timezone):

    text = event.message.message
    account = getattr(event.chat, 'username', None) or str(event.chat_id)

    date_utc = event.message.date
    date_utc = date_utc.replace(tzinfo=ZoneInfo("UTC"))
    date_local = date_utc.astimezone(ZoneInfo(timezone))
    date_local = date_local.strftime("%Y-%m-%d %H:%M:%S")

    dict_infos = {'account': account, 'id': event.message.id, 'date': date_local , 'text': text, 'has_photo': False, 'has_video': False}
    # TODO : photo and video
    # TODO: get the account not the OP

    # Analysis
    if text:
        output = structured_analysis(client_genai, text, prompt, region, languages, model_google='gemini-2.0-flash-lite')
        if output:
            logger.info(f"[{account}]: {output['translation']}")

            results = {
            'text_english': output['translation'],
                'geolocs': [g['location_name'] for g in output['geolocations']], 
                'coordinates': [(g['latitude'], g['longitude']) for g in output['geolocations']], 
                'negative': output['sentiment']['negative'], 
                'neutral': output['sentiment']['neutral'], 
                'positive': output['sentiment']['positive']}

        else:
            logger.warning("Analysis returned None")
            results = {'text_english': '', 'geolocs': [], 'coordinates': [], 'negative': 0.33, 'neutral': 0.34, 'positive': 0.33}    

    else:
        results = {'text_english': '', 'geolocs': [], 'coordinates': [], 'negative': 0.0, 'neutral': 1.0, 'positive': 0.0}

    with open(os.path.join('./data/datamaps/', datamap, 'telegram_gemini.jsonl'), 'a', encoding='utf-8') as file:  # mode append
        json.dump(dict_infos | results, file, ensure_ascii=False)
        file.write('\n')
    

if __name__ == '__main__':

    # Get the current event loop and run the main function
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())