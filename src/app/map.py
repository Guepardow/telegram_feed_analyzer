import numpy as np

from dash import html
import dash_leaflet as dl

def get_locations(messages: list[dict]) -> list[dict]:
    locations = []
    for mid, message in enumerate(messages):
        for geoloc, coords in zip(message['geolocs'], message['coordinates']):
            locations.append({'mid': mid, 'geoloc': geoloc, 'coordinates': coords})

    return locations
    
    
def generate_map(messages, geoconfirmed_locations):

    # Markers for Telegram (blue) and Geoconfirmed (red)
    blue_icon = dict(iconUrl='./assets/marker-icon-blue.png', iconSize=(24,36), iconAnchor=(12, 18))
    red_icon = dict(iconUrl='./assets/marker-icon-red.png', iconSize=(24,36),iconAnchor=(12, 18))

    # Extract the markers of a single Telegram message
    def get_telegram_markers(message):
        """
        Return the list of Markers of all the locations mentioned in a message
        """
        account, date = message['account'], message['date']
        url = f"https://t.me/{account}/{message['id']}"
        text = message['text_english']

        markers = []
        for geoloc, coords in zip(message['geolocs'], message['coordinates']):
            lat, lon = coords

            tooltip = html.Div([
                html.Div([
                    html.Span(account, style={'float': 'left', 'paddingLeft': '3px'}),
                    html.Span(date, style={'float': 'right', 'paddingRight': '3px'})
                    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),
                    html.Div(text, style={'marginTop': '2px', 'padding': '3px'})
                    ], style={'whiteSpace': 'normal', 'width': '300px', 'borderRadius': '8px'})  

            markers.append(dl.Marker(
                position=(lat + np.random.uniform(-1e-4, 1e-4), lon + np.random.uniform(-1e-4, 1e-4)),  # Add noise to avoid overlapping markers
                children=[dl.Tooltip(tooltip), dl.Popup(html.A(url, href=url, target='_blank'))],
                icon=blue_icon))

        return markers

    # Extract the marker of a single Geoconfirmed post
    def get_geoconfirmed_markers(loc):
        """
        Return a Marker of the location mentionned in an post of Geoconfirmed
        """

        lon, lat = loc['geometry']['coordinates']
        sources = loc['properties']['sources']
        description = loc['properties']['description']

        tooltip = html.Div([
            html.Div(description, style={'marginTop': '2px', 'padding': '3px'})
        ], style={'whiteSpace': 'normal', 'width': '300px', 'borderRadius': '8px'})

        popup = html.Div([html.A(source, href=source, target='_blank') for source in sources])

        return dl.Marker(
            position=(lat, lon),
            children=[dl.Tooltip(tooltip), dl.Popup(popup)],
            icon=red_icon)

    # Extract all markers from all Telegram messages
    markers_telegram = [get_telegram_markers(message) for message in messages]
    markers_telegram = [marker for markers in markers_telegram for marker in markers]

    # Extract all markers from all Geoconfirmed posts
    markers_geoconfirmed = [get_geoconfirmed_markers(loc) for loc in geoconfirmed_locations['features']]

    # Create the map
    m = dl.Map(
        [
            dl.TileLayer(
                url='https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png',
                attribution='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors'),
            dl.LayersControl([
                dl.Overlay(dl.LayerGroup(markers_telegram), name='Telegram', checked=True),
                dl.Overlay(dl.LayerGroup(markers_geoconfirmed), name='Geoconfirmed', checked=True),
            ], id='lc', collapsed=False)
        ],
        center=(32, 35),
        zoom=8,
        style={'width': '100%', 'height': '100%'},
        id='map',
    )

    return m