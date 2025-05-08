import os
import json
import click
from loguru import logger


@click.command()
@click.option('--datamap', help='Name of the datamap')
@click.option('--method', help='Name of the method', type=click.Choice(['baseline', 'gemini']))
def main(datamap, method):

    # Initialize an empty list to store all the data
    all_data = []

    # Loop over all accounts
    list_accounts = [f for f in os.listdir(os.path.join('../../data/datamaps', datamap)) if os.path.isdir(os.path.join('../../data/datamaps', datamap, f))]
    for account in list_accounts:

        # Check the number of raw messages 
        with open(os.path.join('../../data/datamaps', datamap, account, "result.json"), encoding='utf-8') as file:
            result = json.load(file)
            n_messages_result = len(result['messages'])
    
        if os.path.exists(os.path.join('../../data/datamaps', datamap, account, f"{method}.json")):

            with open(os.path.join('../../data/datamaps', datamap, account, f"{method}.json"), encoding='utf-8') as file:
                data = json.load(file)
                enhanced_data = [d for d in data if 'text_english' in d]
                all_data.extend(enhanced_data)
            
            if len(enhanced_data) == n_messages_result:
                logger.success(f"Add {method}.json for {account} [{len(enhanced_data)}/{n_messages_result}]")
            else:
                logger.warning(f"Missing messages for {account} [{len(enhanced_data)}/{n_messages_result}]")

        else:
            logger.error(f"Missing {method}.json for {account} [0/{n_messages_result}]")

    logger.info(f"Number of messages: {len(all_data)}")

    # Sort the combined list by the 'date' key
    sorted_data = sorted(all_data, key=lambda x:x['date'])

    # Remove None from coordinates
    for message in sorted_data:
        coordinates_found = [coords[0] is not None for coords in message['coordinates']]
        message['geolocs'] = [geoloc for geoloc, found in zip(message['geolocs'], coordinates_found) if found]
        message['coordinates'] = [coords for coords, found in zip(message['coordinates'], coordinates_found) if found]

    # Write the sorted list to a new file
    with open(os.path.join('../../data/datamaps', datamap, f'telegram_{method}.json'), 'w', encoding='utf-8') as file:
        json.dump(sorted_data, file, indent=4, ensure_ascii=False)  


if __name__ == '__main__':
    main()

# uv run create_datamap.py --datamap syria_241125-241215 --method baseline