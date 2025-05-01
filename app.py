import json
import yaml
import numpy as np
import pandas as pd

import dash
from dash import dcc, html, Input, Output, State, Patch
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
import dash_leaflet as dl
import plotly.express as px

from src.rag import RAG
from src.similarity_search import SimilaritySearch

# --- Geoconfirmed ---

# Define the GeoJSON structure
geojson_data = {
    'type': 'FeatureCollection',
    'features': [
        {
            'type': 'Feature',
            'geometry': {
                'type': 'Point',
                'coordinates': [34.248702, 31.299197]  # Longitude, Latitude
            },
            'properties': {
                'description': "The IDF has issued an evacuation alert over most of the Rafah area that isn't already under IDF control (due to the philadelphi corridor).",
                'sources': ['https://x.com/AvichayAdraee/status/1906595629993967915'],
                'type': 'call'
            }
        }
    ]
}

# --- Telegram message data ---
with open('./data/data_telegram_250331.json', 'r', encoding='utf-8') as f:
    messages = json.load(f)

# --- Locations --

def get_locations(messages: list[dict]) -> list[dict]:
    locations = []
    for mid, message in enumerate(messages):
        for geoloc, coords in zip(message['geolocs_genai'], message['coords_genai']):
            locations.append({'mid': mid, 'geoloc': geoloc, 'coords': coords})

    return locations

telegram_locations = get_locations(messages)

# --- RAG & semantic search systems ---

# Load config and initialize the RAG system and the SimilaritySearch system
with open('./config.yaml') as f:
    config = yaml.safe_load(f)
    GOOGLE_API_KEY = config['secret_keys']['google']['api_key']

rag = RAG(GOOGLE_API_KEY=GOOGLE_API_KEY)
rag.load_collection(host='localhost', port=8001)

similarity_search = SimilaritySearch(GOOGLE_API_KEY=GOOGLE_API_KEY)
similarity_search.load_collection(host='localhost', port=8000)

# --- Map ---
def generate_map(telegram_locations, geoconfirmed_locations):

    locations = []

    for loc in telegram_locations:

        account, date = messages[loc['mid']]['account'], messages[loc['mid']]['date']
        url = f"https://t.me/{account}/{messages[loc['mid']]['id']}"
        text = messages[loc['mid']]['text_english_genai']
        lat, lon = loc['coords']

        tooltip = html.Div([
            html.Div([
                html.Span(account, style={'float': 'left', 'paddingLeft': '3px'}),
                html.Span(date, style={'float': 'right', 'paddingRight': '3px'})
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),
            html.Div(text, style={'marginTop': '2px', 'padding': '3px'})
        ], style={'whiteSpace': 'normal', 'width': '300px', 'borderRadius': '8px'})            

        locations.append({'lat': lat+ np.random.uniform(-1e-4, 1e-4), 'lon': lon+ np.random.uniform(-1e-4, 1e-4),  # Add noise to avoid overlapping markers
        'tooltip': tooltip, 'popup': html.A(url, href=url, target='_blank'), 'icon': dict(
                    iconUrl='./assets/marker-icon-blue.png',
                    iconSize=(24,36),
                    iconAnchor=(12, 18)
                    )})

    if geoconfirmed_locations:
        for loc in geoconfirmed_locations['features']:

            lon, lat = loc['geometry']['coordinates']
            sources = loc['properties']['sources']
            description = loc['properties']['description']

            tooltip = html.Div([
                html.Div(description, style={'marginTop': '2px', 'padding': '3px'})
            ], style={'whiteSpace': 'normal', 'width': '300px', 'borderRadius': '8px'})

            locations.append({
                'lat': lat, 'lon': lon, 
                'icon': dict(
                    iconUrl='./assets/marker-icon-red.png',
                    iconSize=(24,36),
                    iconAnchor=(12, 18)
                    ),
                    'tooltip': tooltip, 
                    'popup': html.Div([html.A(source, href=source, target='_blank') for source in sources])
            })

    # Create the map
    m =  dl.Map(center=(32, 35), zoom=8, children=[

        dl.TileLayer(url='https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png',
            attribution='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors'),

        *[dl.Marker(position=(loc['lat'], loc['lon']),
                    children=[
                        dl.Tooltip(loc['tooltip']),
                        dl.Popup(loc['popup'])
                        ],
                    icon=loc['icon']
                    ) for loc in locations]
    ], style={'width': '100%', 'height': '100%'}, id='map')

    return m

# --- Sentiment chart ---

def precompute_df_sentiment(messages):
    df = pd.DataFrame(messages)
    df['date'] = pd.to_datetime(df['date'])
    df['date_r'] = df['date'].dt.round('5min')  # Round to the most precise interval: 5 minutes
    # so it will be faster to regroup the data and regenerate the chart

    # Rename column of sentiment
    df = df.rename(columns={'negative_genai': 'negative', 'neutral_genai': 'neutral', 'positive_genai': 'positive'})

    # Get the dominant sentiment for each message
    df['dominant_sentiment'] = df[['negative', 'neutral', 'positive']].idxmax(axis=1)

    grouped = df.groupby(['date_r', 'dominant_sentiment']).size().unstack(fill_value=0).reset_index()
    df_long = pd.melt(grouped, id_vars=['date_r'], var_name='sentiment', value_name='count')

    return df_long

df_long = precompute_df_sentiment(messages)

def generate_chart(df_long, interval):

    df_interval = df_long.copy()
    df_interval['date_r'] = df_interval['date_r'].dt.round(interval)

    # Sum the counts for each interval
    df_interval = df_interval.groupby(['date_r', 'sentiment']).sum().reset_index()

    fig = px.bar(df_interval, x='date_r', y='count', color='sentiment',
                 color_discrete_map={'neutral': '#eeeeee', 'negative': '#e74c3c', 'positive': '#2ecc71'},
                 labels={'date_r': '', 'count': 'Number of messages'})

    # Update the layout for dark background
    fig.update_layout(
        plot_bgcolor='#1f1f1f',  
        paper_bgcolor='#1f1f1f',
        font=dict(color='white'),
        yaxis=dict(gridcolor='gray'),
        title_text='Evolution of dominant sentiment', 
        title_x=0.5,

        # Update the legend
        legend=dict(
            orientation='h',  # Horizontal orientation
            yanchor='bottom', # Align to the bottom
            y=-0.45,  # Adjust vertical position
            xanchor='center', # Center the legend
            x=0.2,     # Place legend in the center horizontally
            bgcolor='rgba(0,0,0,0)'  # Transparent background for the legend
        )
    )

    return fig

# --- Message feed ---

def sentiment_to_color(neg, neu, pos):
    if neu > max(neg, pos):
        return 'rgba(255,255,255,1.0)'
    return f"rgba({int(neg*255)}, {int(pos*255)}, 0, 1.0)"

def render_message_html(message):
    user_icon_url = './assets/user_r.png'
    link_icon_url = './assets/link_r.png'
    location_icon_url = './assets/location_r.png'
    photo_icon_url = './assets/photo_r.png'
    video_icon_url = './assets/video_r.png'
    similar_icon_url = './assets/similar_r.png'

    url = f"https://t.me/{message['account']}/{message['id']}"

    color_sentiment = sentiment_to_color(neg=message['negative_genai'], neu=message['neutral_genai'], pos=message['positive_genai'])

    # Start HTML string
    html = f"""
    <style>
        .tooltiptext:hover +.hide {{visibility: visible;}}
	    .hide {{visibility: hidden;}}

    </style>

    <div style="background-color:#2c2c2c;border-left:5px solid {color_sentiment};padding:10px;margin-bottom:8px;margin-right:8px;border-radius:4px;color:white;">
        <div style="display:flex;justify-content:space-between;align-items:center;">

            <div style="display:flex;align-items:center;position: relative;">
                <img class="tooltiptext user-icon" src="{user_icon_url}" height="16" style="margin-right:5px;cursor:pointer;">
                <span class="hide" style="font-size: 10px; width: 140px; background-color: #c2c2c2; color: black; text-align: center; border-radius: 5px; padding: 5px; position: absolute; top: 1px; left: 30px;">Filter on user {message['account']}</span>
                <span style="float:left;vertical-align:top;">{message['account']}</span>
            </div>

            <div style="display:flex;align-items:center;margin-left:auto;">
                <a href="{url}" target="_blank">
                    <img src="{link_icon_url}" height="16" style="margin-right:5px;">
                </a>
                <span style="float:right;">{message['date']}</span>
            </div>
        </div>
        <div style="margin-top:5px;margin-bottom:5px;">{message['text_english_genai']}</div>
        <div style="display:flex;gap:5px;">
            <div style="display:flex;align-items:center;">
    """

    if message.get('coords_genai'):
        for (lat, lon), geoloc in zip(message['coords_genai'], message['geolocs_genai']):
            html += f"""
                <img src="{location_icon_url}" height="16" style="margin-right:5px;cursor:pointer;" title="{geoloc}" data-lat={lat} data-lon={lon} class="location-icon">
            """

    if message.get('has_photo'):
        html += f'<img src="{photo_icon_url}" height="16" style="margin-right:5px;">'
    
    if message.get('has_video'):
        html += f'<img src="{video_icon_url}" height="16">'

    html += f"""
            </div>
            <div style="margin-left:auto;cursor:pointer;margin-right: 0;">
                <img class="tooltiptext similar-icon" src="{similar_icon_url}" height="16" style="margin-right:-120px;cursor:pointer;">
                <span class="hide" style="font-size: 10px; width: 140px; background-color: #c2c2c2; color: black; text-align: center; border-radius: 5px; padding: 5px; position: relative; top: 0px; right: 40px;">Search for similar messages</span>
            </div>
            
        </div>
    </div>
    """

    return html

for idx, msg in enumerate(messages):
    msg['message_html'] = render_message_html(msg)

df = pd.DataFrame(messages)

def generate_grid(messages):

    columnDefs = [
    {'field': 'message_html', 'cellRenderer': 'RenderHTML'},
    {'field': 'account', 'hide': True},  # Invisible column
    {'field': 'sim', 'hide': True}
    ]

    grid = dag.AgGrid(
        id='messages-dag',
        columnDefs=columnDefs,
        rowData=messages,
        columnSize='responsiveSizeToFit',
        dashGridOptions={
            'headerHeight':0, 
            'rowStyle': { 'border': 'none'},
            'suppressCellFocus': True
            },
        style={'height': '100%', 'width': '100%'},
        className='no-border-grid',
        defaultColDef={
            'sortable': True, 'filter': True,
            'cellStyle': {'backgroundColor': '#3c3c3c', 'color': 'white', 'padding': '0px'},
            'wrapText': True,  # Ensure text wraps within the cell
            'autoHeight': True  # Automatically adjust the height of the row based on content
        }
    )

    return grid

grid = generate_grid(messages)

# --- Initialize Dash app ---

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = 'Telegram Feed Analyzer'

# --- Styles & Layout ---

CARD_STYLE = {'backgroundColor': '#3c3c3c', 'borderRadius': '8px', 'padding': '8px', 'height': '100%', 'margin':'0px'}
LABEL_STYLE = {'marginBottom': '4px', 'fontWeight': 'bold', 'fontSize': '16px'}

app.layout = dbc.Container([

    # Header
    dbc.Row([
        dbc.Col(html.Div('Telegram Feed Analyzer', 
        style={'fontFamily': 'monospace', 'fontSize': '24px', 'marginTop': '8px', 'marginLeft': '8px', 'marginBottom': '-4px','color': '#ffffff'})
        )
    ], justify='center'),

    # Horizontal rule
    dcc.Store(id='is_filtered', data=False),
    html.Hr(),

    # dbc.Row([
    #     dbc.Col([
    #         dbc.Row([
    #             dbc.Col([
    #                 html.Label('Date (UTC)', style=LABEL_STYLE),
    #                 dcc.DatePickerSingle(
    #                     id='date-picker',
    #                     date='2025-12-31',
    #                     style={'width': '100%'}
    #                 )
    #             ], width=4),
    #             dbc.Col([
    #                 html.Label('Duration', style=LABEL_STYLE),
    #                 dcc.Dropdown(
    #                     id='duration-dropdown',
    #                     options=[
    #                         {'label': '24h', 'value': '24h'},
    #                         {'label': '4h', 'value': '4h'},
    #                         {'label': '30min', 'value': '30min'},
    #                         {'label': '5min', 'value': '5min'},
    #                     ],
    #                     value='24h',
    #                     clearable=False,
    #                 )
    #             ], width=4),
    #             dbc.Col([
    #                 html.Label('Account', style=LABEL_STYLE),
    #                 dcc.Dropdown(
    #                     id='account-dropdown',
    #                     options=[{'label': 'account_name_1', 'value': 'account_name_1'}],
    #                     value='account_name_1',
    #                     clearable=False,
    #                 )
    #             ], width=4)
    #         ])
    #     ], width=12)
    # ], className='mb-2'),

    # Main Content
    dbc.Row([

        # Left Column - Messages Feed
        dbc.Col([
            dbc.Card([

                html.Div([
                    dcc.Input(id='quick-filter-input', placeholder='Filter on keywords ...', style={'width': '100%', 'backgroundColor': '#1f1f1f', 'color': '#ffffff', 'borderRadius': '4px', 'border': 'none', 'padding': '8px', 'marginBottom': '10px'}),

                    # Messages with dag
                    html.Div([grid], id='messages-feed', style={'height': '80vh', 'marginx': '8px'}),
                    html.Button('Reset filters \u27f3', id='reset-button', style={'width': '100%', 'backgroundColor': 'grey', 'border': 'none', 'borderRadius': '4px', 'margin-top': '8px'})
                ]),

            ], style=CARD_STYLE)
        ], width=3, style={'padding-right': '0px'}),

        # Center Column - QA RAG
        dbc.Col([
            dbc.Card([
                html.Div([
                    dcc.Input(id='question-input', type='text', placeholder='Enter your question to the RAG system ...', style={'width': '85%', 'backgroundColor': '#1f1f1f', 'color': '#ffffff', 'borderRadius': '4px', 'border': 'none', 'padding': '8px'}),
                    html.Button('Run \u21b2', id='run-button', style={'width': '15%', 'backgroundColor': 'grey', 'borderRadius': '4px', 'border': 'none'}),
                    
                ], style={'display': 'flex', 'gap': '10px', 'marginBottom': '10px'}),
                dcc.Loading(
                    html.Div(id='response-rag', 
                             style={'flex': 1, 'height': '83vh', 'backgroundColor': '#1f1f1f', 'borderRadius': '5px', 
                                    'padding': '10px', 'overflowY': 'auto'}
                            ),
                    id='loading-component', 
                    style={'flex': 1, 'height': '83vh', 'backgroundColor': '#1f1f1f', 'borderRadius': '5px', 'padding': '10px', 'color': 'white'}),
            ], style=CARD_STYLE)
        ], width=3, style={'padding-right': '0px'}),

        # Right Column - Map and Sentiment Chart
        dbc.Col([
            dbc.Card([
                html.Div(children=generate_map(telegram_locations, None), style={'flex': 1, 'height': '50vh', 'backgroundColor': '#1f1f1f', 'borderRadius': '5px', 'padding': '0px', 'marginBottom': '10px'}),

                dcc.Checklist(
                    id='map-checklist',
                    options=[
                        {'label': 'Telegram', 'value': 'telegram'},
                        {'label': 'Geoconfirmed', 'value': 'geoconfirmed'}],
                        value=['telegram'],
                        inputStyle={'margin-right': '5px'},
                        style={'position': 'absolute', 'top': '0px', 'right': '0px', 'z-index': '1000', 
                        'backgroundColor': '#3c3c3c', 'color': '#ffffff', 'borderRadius': '8px', 
                        'padding-left': '12px', 'padding-right': '20px', 'padding-top': '16px', 'padding-bottom': '8px'}
                        ),
                
                dcc.Graph(id='sentiment-chart', figure=generate_chart(df_long, '30min'), style={'height': '33vh'}),

                dcc.RadioItems(id='interval', options=[
                    {'label': '5min', 'value': '5min'},
                    {'label': '30min', 'value': '30min'},
                    {'label': '4h', 'value': '4h'},
                    {'label': '24h', 'value': '24h'}
                    ],
                    value='30min',
                    labelStyle={'display': 'inline-block', 'margin-right': '10px'},
                    inputStyle={'margin-right': '5px'},
                    style={'position': 'absolute', 'bottom': '0px', 'right': '0px', 'z-index': '1000', 
                        'backgroundColor': '#3c3c3c', 'color': '#ffffff', 'borderRadius': '8px', 
                        'padding-left': '12px', 'padding-right': '20px', 'padding-top': '8px', 'padding-bottom': '16px'}
                )
            ], style=CARD_STYLE)
        ], width=6)
    ])

], fluid=True)

# --- Callbacks ---

@app.callback(
    Output('run-button', 'style'),
    Input('question-input', 'value'),
    prevent_initial_call=True
)
def update_button_color(question):
    if question:
        return {'width': '15%', 'backgroundColor': '#4CAF50', 'borderRadius': '4px', 'border': 'none'}
    return {'width': '15%', 'backgroundColor': 'grey', 'borderRadius': '4px', 'border': 'none'}

@app.callback(
    Output('sentiment-chart', 'figure'),
    Input('interval', 'value'),
    prevent_initial_call=True
)
def update_sentiment_chart(interval):
    return generate_chart(df_long, interval)

@app.callback(
    Output('messages-feed', 'children'),
    Output('is_filtered', 'data', allow_duplicate=True),
    Output('reset-button', 'style', allow_duplicate=True),
    Input('reset-button', 'n_clicks'),
    prevent_initial_call=True
)
def reset_grid(n_clicks):

    return grid, False, {'width': '100%', 'border': 'none', 'borderRadius': '4px', 'margin-top': '8px', 'backgroundColor': 'grey'}


@app.callback(
    Output('response-rag', 'children'),
    Input('run-button', 'n_clicks'),
    State('question-input', 'value'),
    prevent_initial_call=True
)
def run_query(n_clicks, query):
    if not query:
        return 'Please enter a query.'
    answer = rag.query(query=query, n_results=20)
    return dcc.Markdown([answer])

@app.callback(
    Output('messages-dag', 'filterModel'),
    Output('messages-dag', 'rowData', allow_duplicate=True),
    Output('reset-button', 'style'),
    Output('is_filtered', 'data'),
    Input('messages-dag', 'cellRendererData'),
    Input('is_filtered', 'data'),
    State('messages-dag', 'rowData'),
    prevent_initial_call=True
)
def update_grid(cellRendererData, is_filtered, current_row_data):
    # TODO: reset call automatically this function

    style_common = {'width': '100%', 'border': 'none', 'borderRadius': '4px', 'margin-top': '8px'}

    if cellRendererData and 'value' in cellRendererData:
        # Click to filter on account
        if ('filterAccount' in cellRendererData['value']) and (not is_filtered):

            filter_model = {'account': {'filterType': 'text', 'type': 'equals', 
                                        'filter': cellRendererData['value']['filterAccount']}}

            return filter_model, dash.no_update, style_common | {'backgroundColor': '#4CAF50'}, True

        # Click to find similar messages
        elif ('showSimilar' in cellRendererData['value']) and (not is_filtered):
            # TODO: slow compared to filterAccount: 500-700ms vs 100-200ms
            # TODO: a sort is better, no ? faster and simpler

            # Format the message 
            idx = cellRendererData['rowIndex']
            message, date = messages[idx]['text_english_genai'],  messages[idx]['date']
            query_message = f"[Date: {date}] {message}"

            # Search for the top k
            results = similarity_search.query(query_message, n_results=100)
            indices = [int(mid) for mid in results['ids'][0]]

            return dash.no_update, [current_row_data[i] for i in indices], style_common | {'backgroundColor': '#4CAF50'}, True

        elif 'zoomLoc' in cellRendererData['value']:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    # When we click on reset or if we try to filter again 
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update


@app.callback(
    Output('map', 'center'),
    Output('map', 'zoom'),
    Input('messages-dag', 'cellRendererData'),
    prevent_initial_call=True
)
def zoom_to_marker(cellRendererData):
    # TODO: this is super fast, but it calls another callback which is slow (100ms vs 3ms)

    if cellRendererData and 'value' in cellRendererData:

        if 'zoomLoc' in cellRendererData['value']:
            lat, lon, _ = cellRendererData['value']['zoomLoc']
            lat, lon = float(lat), float(lon)

            return (lat, lon), 14
    
    return dash.no_update

@app.callback(
    Output('messages-dag', 'dashGridOptions'),
    Input('quick-filter-input', 'value'),
    prevent_initial_call=True
)
def update_filter(filter_value):
    newFilter = Patch()
    newFilter['quickFilterText'] = filter_value
    return newFilter

@app.callback(
    Output('map', 'children'),
    Input('map-checklist', 'value'),
    prevent_initial_call=True
)
def update_map(selected_layers):
    telegram = telegram_locations if 'telegram' in selected_layers else []
    geoconfirmed = geojson_data if 'geoconfirmed' in selected_layers else []

    return generate_map(telegram, geoconfirmed)


if __name__ == '__main__':
    app.run(debug=True)

# uv run app.py