import os
import json
import yaml
import click
import pandas as pd
from loguru import logger
from datetime import datetime, timedelta

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, Patch

from src.rag import RAG
from src.similarity_search import SimilaritySearch

from src.app.grid import render_message_html, generate_grid
from src.app.map import get_locations, generate_map
from src.app.chart import precompute_df_sentiment, generate_chart

# --- List of datamaps ---

list_datamaps = [f for f in os.listdir('./data/datamaps') if os.path.isdir(os.path.join('./data/datamaps', f))]

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

with open('./data/datamaps/syria_241125-241215/telegram_baseline.json', 'r', encoding='utf-8') as f:
    messages = json.load(f)[:100]

telegram_locations = get_locations(messages)

# Load config and initialize the RAG system and the SimilaritySearch system
with open('./config.yaml') as f:
    config = yaml.safe_load(f)
    GOOGLE_API_KEY = config['secret_keys']['google']['api_key']

rag = RAG(GOOGLE_API_KEY=GOOGLE_API_KEY)
similarity_search = SimilaritySearch(GOOGLE_API_KEY=GOOGLE_API_KEY)

df_long = precompute_df_sentiment(messages)

for idx, msg in enumerate(messages):
    msg['message_html'] = render_message_html(msg)

df = pd.DataFrame(messages)

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
        dbc.Col(
            html.Div(
                [
                    html.Div('Telegram Feed Analyzer',
                        style={'fontFamily': 'monospace', 'fontSize': '24px', 'marginTop': '8px',
                            'marginLeft': '8px', 'marginBottom': '-4px','color': '#ffffff'}),
                    html.Img(src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f30d/512.gif", width=32, height=32, 
                        style={'marginLeft': '8px'})
                ],
                className='d-flex align-items-center',
                style={'margin-top': '8px'}, 
            ), width=4,
        ),   

        dbc.Col(
            html.Div(
                [
                    html.Div('🗺️', className='pr-2', style={'fontSize': '25px'}),
                    dcc.Dropdown(
                        id='map-input',
                        options=[{'label': label, 'value': label} for label in list_datamaps],
                        placeholder='Select a datamap',
                        className='dark-theme-dropdown',
                        style={'width': '90%'}
                    )
                ],
                className='d-flex align-items-center',
                style={'margin-top': '8px'},
            ), width=3,
        ),

        dbc.Col(
            html.Div(
                [
                    html.Div('📆', className='pr-2', style={'fontSize': '25px'}),
                    html.Button('\u27f3', id='reset-date', title='Reset date', style={'margin-right': '4px', 'margin-left': '4px', 'paddingLeft': '8px', 'paddingRight': '8px', 'borderRadius': '4px'}),
                    html.Button('-', id='decrease-date', title='Substract 6 hours', n_clicks=0, style={'margin-right': '4px', 'margin-left': '4px', 'paddingLeft': '8px', 'paddingRight': '8px', 'borderRadius': '4px', 'fontFamily': 'monospace'}),
                    dcc.Input(
                        id='date-input',
                        type='text',
                        placeholder='Waiting for a map-database',
                        readOnly=False,  # TODO: check if any error
                        className='text-center bg-black text-white',
                        style={'width': '90%', 'border': '1px solid #333', 'borderRadius': '4px', 'paddingTop': '6px', 'paddingBottom': '6px'}
                    ),
                    html.Button('+', id='increase-date', title='Add 6 hours', n_clicks=0, style={'margin-right': '4px', 'margin-left': '4px', 'paddingLeft': '8px', 'paddingRight': '8px', 'borderRadius': '4px', 'fontFamily': 'monospace'}),
                ],
                className='d-flex align-items-center',
                style={'margin-top': '8px'},
            ), width=3,
        ),

        dbc.Col(
            html.Div(
                [
                    html.Div('⌛', className='pr-2', style={'fontSize': '25px'}),
                    dcc.Dropdown(
                        id='duration-input',
                        options=[{'label': f'{n}h', 'value': n} for n in [6, 12, 24, 48]],
                        value=24,
                        placeholder='Select a duration',
                        className='dark-theme-dropdown',
                        style={'width': '90%'}
                    )
                ],
                className='d-flex align-items-center',
                style={'margin-top': '8px'},
            ), width=1, 
        ),

        dbc.Col(
            html.Div([html.Button('?', id='info', style={'margin-right': '4px', 'margin-left': '4px', 'paddingLeft': '8px', 'paddingRight': '8px', 'border': '1px solid #333', 'borderRadius': '16px'})],
                style={'margin-top': '12px'}
            ), width=1,
        )

    ]),

    # Horizontal rule
    html.P(id='messages-stat', style={'fontSize': '12px', 'marginLeft': '8px','fontFamily': 'monospace'}),
    dcc.Store(id='messages'),
    dcc.Store(id='messages-dag-init'),
    dcc.Store(id='telegram_locations'),
    dcc.Store(id='geoconfirmed_locations'),
    dcc.Store(id='json_sentiment'),
    dcc.Store(id='is_filtered', data=False),
    html.Hr(style={'marginTop': '8px','marginBottom': '16px'}),

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
                    style={'flex': 1, 'height': '83vh', 'backgroundColor': '#1f1f1f', 'borderRadius': '5px', 'padding': '10px'}),
            ], style=CARD_STYLE)
        ], width=3, style={'padding-right': '0px'}),

        # Right Column - Map and Sentiment Chart
        dbc.Col([
            dbc.Card([
                html.Div(children=generate_map(messages, geojson_data), style={'flex': 1, 'height': '50vh', 'backgroundColor': '#1f1f1f', 'borderRadius': '5px', 'padding': '0px', 'marginBottom': '10px'}),
                
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
    Output('date-input', 'value'),
    Input('reset-date', 'n_clicks'),
    Input('map-input', 'value'),
    prevent_initial_call=False
)
def reset_date(n_clicks, map_name):
    """
    Reset the date to the initial date if the button 'reset' is clicked
    or if the map-database changes
    """

    if map_name:
        with open(os.path.join('./data/datamaps', map_name, 'map-config.yaml')) as f:
            map_config = yaml.safe_load(f)

        map_date_start = map_config['date']['start']
        map_date_start = datetime.strptime(map_date_start, '%Y-%m-%d %H:%M:%S')
        map_date_start = map_date_start.strftime('%Y-%m-%d %H:%M')

        return map_date_start

@app.callback(
    Output('date-input', 'value', allow_duplicate=True),
    Input('increase-date', 'n_clicks'),
    Input('decrease-date', 'n_clicks'),
    State('date-input', 'value'),
    prevent_initial_call=True
)
def update_date(increase_clicks, decrease_clicks, current_date):
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_date

    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    date_obj = datetime.strptime(current_date, '%Y-%m-%d %H:%M')

    if button_id == 'increase-date':
        date_obj += timedelta(hours=6)
    elif button_id == 'decrease-date':
        date_obj -= timedelta(hours=6)

    return date_obj.strftime('%Y-%m-%d %H:%M')

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
        return 'Please enter a question.'
    answer = rag.query(query=query, n_results=20)
    return dcc.Markdown([answer])

@app.callback(
    Output('messages-dag', 'filterModel'),
    Output('messages-dag', 'rowData', allow_duplicate=True),
    Output('reset-button', 'style'),
    Output('is_filtered', 'data'),
    Output('map', 'center'),
    Output('map', 'zoom'),
    Input('messages-dag', 'cellRendererData'),
    Input('is_filtered', 'data'),
    State('messages-dag', 'rowData'),
    prevent_initial_call=True
)
def update_grid(cellRendererData, is_filtered, current_row_data):

    style_common = {'width': '100%', 'border': 'none', 'borderRadius': '4px', 'margin-top': '8px'}

    if cellRendererData and 'value' in cellRendererData:
        # Click to filter on account
        if ('filterAccount' in cellRendererData['value']) and (not is_filtered):

            filter_model = {'account': {'filterType': 'text', 'type': 'equals', 
                                        'filter': cellRendererData['value']['filterAccount']}}

            return filter_model, dash.no_update, style_common | {'backgroundColor': '#4CAF50'}, True, dash.no_update, dash.no_update

        # Click to find similar messages
        elif ('showSimilar' in cellRendererData['value']) and (not is_filtered):

            # Format the message 
            idx = cellRendererData['rowIndex']
            message, date = messages[idx]['text_english'],  messages[idx]['date']
            query_message = f"[Date: {date}] {message}"

            # Search for the top k
            results = similarity_search.query(query_message, n_results=100)
            indices = [int(mid) for mid in results['ids'][0]]

            return dash.no_update, [current_row_data[i] for i in indices], style_common | {'backgroundColor': '#4CAF50'}, True, dash.no_update, dash.no_update

        elif 'zoomLoc' in cellRendererData['value']:

            lat, lon, _ = cellRendererData['value']['zoomLoc']
            lat, lon = float(lat), float(lon)

            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, (lat, lon), 14

    # When we click on reset or if we try to filter again 
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

@app.callback(
    Output('messages-dag', 'dashGridOptions'),
    Input('quick-filter-input', 'value'),
    prevent_initial_call=True
)
def update_filter(filter_value):
    newFilter = Patch()
    newFilter['quickFilterText'] = filter_value
    return newFilter

@click.command()
@click.option('--no-server', is_flag=True, help='Run the app without the servers for similarity search and RAG')
def main(no_server):

    if no_server:
        logger.warning("""
        Servers are off: similarity search and RAG are disabled.
        To enable them, remove the flag '--no-server', update config.yaml with a GOOGLE_API_KEY and start both servers.\n
        See instructions at https://github.com/Guepardow/telegram_feed_analyzer
        """)

    else:
        # Connect to the servers
        similarity_search.load_collection(host='localhost', port=8000)
        rag.load_collection(host='localhost', port=8001)

    app.run_server(debug=True)


if __name__ == '__main__':

    main()

# uv run app.py
# uv run app.py --no_server
