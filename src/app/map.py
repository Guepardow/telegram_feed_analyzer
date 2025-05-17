import os
import re
import yaml
from zipfile import ZipFile
from bs4 import BeautifulSoup
from datetime import datetime
from loguru import logger
from time import perf_counter

from dash import html


def get_telegram_locations(all_messages: list[dict]) -> list[dict]:
    """
    Return a list of all locations mentionned in Telegram posts
    """

    # Format the tooltip for a message
    def get_locations(message):

        account, date = message['account'], message['date']
        text = message['text_english']
        url = f"https://t.me/{account}/{message['id']}"
        # has_photo, has_video = message['has_photo'], message['has_video']

        locations = []
        for geoloc, coords in zip(message['geolocs'], message['coordinates']):
            lat, lon = coords

            tooltip = html.Div([
                html.Div([
                    html.Span(account, style={'float': 'left', 'paddingLeft': '3px'}),
                    html.Span(date, style={'float': 'right', 'paddingRight': '3px'})
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),
                html.Div(text, style={'marginTop': '2px', 'padding': '3px'}),
                # html.Img(src='./assets/photo.png', height=16) if has_photo else None,
                # html.Img(src='./assets/video.png', height=16) if has_video else None,
                ], style={'whiteSpace': 'normal', 'width': '300px', 'borderRadius': '8px'})  

            popup = html.A(url, href=url, target='_blank')

            locations.append({'position': (lat, lon), 'tooltip': tooltip, 'popup': popup, 'date': date})

        return locations

    # List of all locations mentioned in Telegram posts
    telegram_locations = []
    for message in all_messages:
        telegram_locations.extend(get_locations(message))

    return telegram_locations


def get_geoconfirmed_locations(datamap:str) -> list[dict]:

    def get_description(full_description: str) -> str:
        """
        Return the textual description of an event
        """
        pattern = r'(?:\d{1,2}:\d{2}\s?-\s?\d{1,2}:\d{2}[ :-]*)?(.+?)\s*Source'
        return re.search(pattern, full_description, re.DOTALL).group(1).strip()

    def get_sources(full_description):
        
        try:
            pattern = r'Source(.*?)Geolocation'  # match all URLs between "Source" and "Geolocation"
            urls = re.findall(r'https?://\S+', re.search(pattern, full_description, re.DOTALL).group(1))
            
        except:  # noqa: E722
            # There is no Geolocation, since it may be a satellite image
            
            pattern = r'Source(.*?)$'  # match all URLs after "Source" 
            urls = re.findall(r'https?://\S+', re.search(pattern, full_description, re.DOTALL).group(1))
            
        return urls

    # Open datamap to get the list of Geoconfirmed maps to load
    with open(os.path.join('data/datamaps', datamap, 'datamap-config.yaml')) as f:
        config = yaml.safe_load(f)
        list_maps = config['geoconfirmed']

    geoconfirmed_locations = []
    for mapname in list_maps:

        # Find the latest version of Geoconfirmed
        filename = sorted(os.listdir(os.path.join('data/geoconfirmed', mapname)))[-1]
        
        tic = perf_counter()

        # Open KMZ map and parse it
        with ZipFile(os.path.join('data/geoconfirmed', mapname, filename)) as kmz:
            with kmz.open('doc.kml') as kml_file:
                kml = kml_file.read()
        soup = BeautifulSoup(kml, 'lxml-xml')  # faster than 'xml'
        placemarks = soup.find_all('Placemark')
        logger.debug(f"\tElapsed time for opening KMZ file: {perf_counter() - tic:0.3f} sec")
        
        # Load locations that fit the date range
        for placemark in placemarks:
    
            name_loc = placemark.find().text
            if (name_loc != 'Dummy placemark') and ('Front line' not in name_loc) and ('Frontline' not in name_loc):
                coordinates = placemark.coordinates.text
                if len(coordinates) < 100:

                    # Parse date of the geolocated event
                    date_str = placemark.find("name").text
                    date = datetime.strptime(date_str, "%d %b %Y").date()

                    # Description of the event
                    full_description = placemark.find("description").text
                    description = get_description(full_description)

                    # Sources of the events
                    sources = get_sources(full_description)
                    source_links = [element for source in sources for element in [html.A(source, href=source, target='_blank'), html.Br()]]
                    if source_links: # Remove the last html.Br element to avoid an extra line break at the end
                        source_links.pop()

                    popup = html.Div(source_links, style={'whiteSpace': 'normal', 'width': '400px', 'borderRadius': '8px'})

                    # Coordinates
                    coordinates = placemark.find("coordinates").text
                    lon, lat, _ = coordinates.split(',')

                    # Tooltip
                    tooltip = html.Div([
                        html.Div([html.Span(date, style={'float': 'right', 'paddingRight': '3px'})]),
                        html.Div(description, style={'marginTop': '2px', 'padding': '3px'})
                        ], style={'whiteSpace': 'normal', 'width': '300px', 'borderRadius': '8px'})

                    geoconfirmed_locations.append({'date': date, 'tooltip': tooltip, 'popup': popup, 'position': (float(lat), float(lon))})

    return geoconfirmed_locations