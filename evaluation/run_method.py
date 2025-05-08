import os
import sys
import json
import yaml
import click
from tqdm import tqdm
from google import genai
from loguru import logger

sys.path.append('..')
from src.gemini.structured_output import structured_analysis, COMBINED_PROMPT

LIST_GEMINI = ['gemini-2.0-flash', 'gemini-2.0-flash-lite', 'gemini-2.5-flash-preview-04-17', 'gemini-1.5-flash']

# 'gemini-2.0-flash-lite': 30/min, 1500/day
# 'gemini-2.0-flash': 15/min, 1000/day
# 'gemini-1.5-flash': 15/min, 500/day
# 'gemini-2.5-flash-preview-04-17': 10/min, 500/day


@click.command()
@click.option('--method', required=True, type=click.Choice(LIST_GEMINI), help="Name of the Gemini model")
def main(method):

    # Login to the Google API
    with open('../config.yaml') as f:
        config = yaml.safe_load(f)
        GOOGLE_API_KEY = config['secret_keys']['google']['api_key']

    client = genai.Client(api_key=GOOGLE_API_KEY)

    for model in  client.models.list():
        print(model.name)

    # Open data
    with open('./data/sample50.json', encoding='utf-8') as file:
        messages = json.load(file)
        REGION = "the Middle East (mainly, Gaza, Israel and West Bank)" 
        LANGUAGES = "Arabic, Hebrew, or English"

    # Prediction over each message
    for i, message in tqdm(enumerate(messages), total=len(messages)):

        output = structured_analysis(client, message['text'], prompt_template=COMBINED_PROMPT, region=REGION, languages=LANGUAGES, model_google=method)
        if output:
            messages[i] =  message | {'text_english': output['translation'], 
            'geolocs': [g['location_name'] for g in output['geolocations']], 
            'coordinates': [(g['latitude'], g['longitude']) for g in output['geolocations']], 
            'negative': output['sentiment']['negative'], 'neutral': output['sentiment']['neutral'], 'positive': output['sentiment']['positive']} 
        else:
            logger.warning(f"None returned as output by Google API at message {i}")

    with open(f"./results/{method}.json", 'w', encoding='utf-8') as file:
        json.dump(messages, file, indent=4, ensure_ascii=False)  


if __name__ == '__main__':
    main()