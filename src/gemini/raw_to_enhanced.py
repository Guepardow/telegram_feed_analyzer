import os
import sys
import json
import yaml
import click
from tqdm import tqdm
from google import genai
from loguru import logger

from structured_output import structured_analysis, COMBINED_PROMPT

sys.path.append('..')
from data_telegram.extractor import extract_message


@click.command()
@click.option('--datamap', help='Name of the datamap')
@click.option('--account', help='Name of the account')
def main(datamap, account):

    # Login to the Google API
    config_path = os.path.join(os.path.dirname(__file__), '../../config.yaml')
    with open(config_path) as f:
        config = yaml.safe_load(f)
        GOOGLE_API_KEY = config['secret_keys']['google']['api_key']
    
    # Get the configuration of the datamap
    datamap_config_path = os.path.join(os.path.join('../../data/datamaps', datamap, 'datamap-config.yaml'))
    with open(datamap_config_path) as f:
        config = yaml.safe_load(f)
        REGION = config['map']['region']
        LANGUAGES = config['map']['languages']

    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Create a Gemini file if it does not exist
    if not os.path.exists(os.path.join('../../data/datamaps', datamap, account, 'gemini.json')):

        # Open the result.json
        with open(os.path.join('../../data/datamaps', datamap, account, 'result.json'), encoding='utf-8') as file:
            result = json.load(file)

        # Extract raw messages
        messages = [extract_message(m, account) for m in result['messages']]

        # Save it as gemini.json
        with open(os.path.join('../../data/datamaps', datamap, account, 'gemini.json'), 'w', encoding='utf-8') as file:
            json.dump(messages, file, indent=4, ensure_ascii=False)  

    # Open the gemini.json
    with open(os.path.join('../../data/datamaps', datamap, account, 'gemini.json'), encoding='utf-8') as file:
        messages = json.load(file)

    # Iterate over messages
    for i, message in tqdm(enumerate(messages), desc=f"Converting messages of {account}", leave=True, total=len(messages)):

        if 'text_english' not in message:

            if not message['text']:
                messages[i] = message | {'text_english': '', 'geolocs': [], 'coordinates': [], 'negative': 0.0, 'neutral': 1.0, 'positive': 0.0}

            else:

                output = structured_analysis(client, message['text'], prompt_template=COMBINED_PROMPT, region=REGION, languages=LANGUAGES)
                if output:
                    messages[i] =  message | {'text_english': output['translation'], 
                    'geolocs': [g['location_name'] for g in output['geolocations']], 
                    'coordinates': [(g['latitude'], g['longitude']) for g in output['geolocations']], 
                    'negative': output['sentiment']['negative'], 'neutral': output['sentiment']['neutral'], 'positive': output['sentiment']['positive']} 
                else:
                    logger.warning(f"None returned as output by Google API at message id {message['id']}")

        # Early saving in case of an error
        if i % 50 == 0:
            with open(os.path.join('../../data/datamaps', datamap, account, 'gemini.json'), 'w', encoding='utf-8') as file:
                json.dump(messages, file, indent=4, ensure_ascii=False)

    # Save the final file
    with open(os.path.join('../../data/datamaps', datamap, account, 'gemini.json'), 'w', encoding='utf-8') as file:
        json.dump(messages, file, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    main()