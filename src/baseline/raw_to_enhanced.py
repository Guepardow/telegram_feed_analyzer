import os
import sys
import json
import click
import asyncio
from tqdm import tqdm

from translation import translate_with_googletrans
from geolocation import load_model_geolocation, get_location_name, get_coordinates
from sentiment_analysis import load_model_sentiment, get_sentiment

sys.path.append('..')
from data_telegram.extractor import extract_message


@click.command()
@click.option('--datamap', help='Name of the datamap')
@click.option('--account', help='Name of the account')
def main(datamap, account):

    # Load models
    model_geoloc = load_model_geolocation()
    tokenizer_sentiment, model_sentiment = load_model_sentiment()

    # Baseline file
    if not os.path.exists(os.path.join('../../data/datamaps', datamap, account, 'baseline.json')):

        # Open the result.json
        with open(os.path.join('../../data/datamaps', datamap, account, 'result.json'), encoding='utf-8') as file:
            result = json.load(file)

        # Extract raw messages
        messages = [extract_message(m, account) for m in result['messages']]

        with open(os.path.join('../../data/datamaps', datamap, account, 'baseline.json'), 'w', encoding='utf-8') as file:
            json.dump(messages, file, indent=4, ensure_ascii=False)  
    else:

        # Open the baseline.json
        with open(os.path.join('../../data/datamaps', datamap, account, 'baseline.json'), encoding='utf-8') as file:
            messages = json.load(file)

    # Iterate over messages
    for i, message in tqdm(enumerate(messages), desc=f"Converting messages of {account}", leave=True, total=len(messages)):

        if 'text_english' not in message:

            if message['text']:

                text_english = asyncio.run(translate_with_googletrans(message['text']))
                geolocs = get_location_name(text_english, model_geoloc)
                coordinates = [get_coordinates(geoloc) for geoloc in geolocs]
                sentiments = get_sentiment(text_english, tokenizer_sentiment, model_sentiment)

                messages[i] =  message | {'text_english': text_english, 'geolocs': geolocs, 'coordinates': coordinates} | sentiments

            else:
                messages[i] =  message | {'text_english': '', 'geolocs': [], 'coordinates': []} | {'negative': 0.0, 'neutral': 1.0, 'positive': 0.0}

        # Early saving in case of an error
        if i % 10 == 0:
            with open(os.path.join('../../data/datamaps', datamap, account, 'baseline.json'), 'w', encoding='utf-8') as file:
                json.dump(messages, file, indent=4, ensure_ascii=False)

    # Save the final file
    with open(os.path.join('../../data/datamaps', datamap, account, 'baseline.json'), 'w', encoding='utf-8') as file:
        json.dump(messages, file, indent=4, ensure_ascii=False)


if __name__ == '__main__':
    main()