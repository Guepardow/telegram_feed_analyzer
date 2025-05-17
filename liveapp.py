import os
import json
import yaml
import click
from loguru import logger
from typing import Optional
from datetime import datetime
from time import perf_counter

import dash
import dash_leaflet as dl
import dash_ag_grid as dag
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, Patch

from src.gemini.rag import RAG
from src.gemini.similarity_search import SimilaritySearch

from src.app.grid import render_message_html
from src.app.map import get_telegram_locations
from src.app.chart import generate_chart

# --- List of datamaps ---

list_datamaps = [f for f in os.listdir('./data/datamaps') if os.path.isdir(os.path.join('./data/datamaps', f))]

# --- Connect to Chroma Databases ---

with open('./config.yaml') as f:
    config = yaml.safe_load(f)
    GOOGLE_API_KEY = config['secret_keys']['google']['api_key']

rag = RAG(GOOGLE_API_KEY=GOOGLE_API_KEY)
similarity_search = SimilaritySearch(GOOGLE_API_KEY=GOOGLE_API_KEY)

# --- Initialize Dash app ---

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
app.title = 'Telegram Live Feed Analyzer'

CARD_STYLE = {'backgroundColor': '#3c3c3c', 'borderRadius': '8px', 'padding': '8px', 'height': '100%', 'margin':'0px'}
LABEL_STYLE = {'marginBottom': '4px', 'fontWeight': 'bold', 'fontSize': '16px'}

app.layout = dbc.Container([

    # Header
    dbc.Row([
        dbc.Col(
            html.Div(
                [
                    html.Div('Telegram Live Feed Analyzer',
                        style={'fontFamily': 'monospace', 'fontSize': '24px', 'marginTop': '8px',
                            'marginLeft': '8px', 'marginBottom': '-4px','color': '#ffffff'}),
                    html.Img(src="https://fonts.gstatic.com/s/e/notoemoji/latest/1f6a8/512.gif", width=32, height=32, 
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
                        id='datamap',
                        value='live',
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
                    dcc.Input(
                        id='date-input',
                        type='text',
                        placeholder='Waiting for a map-database',
                        readOnly=False,  # TODO: check if any error
                        className='text-center bg-black text-white',
                        style={'width': '90%', 'border': '1px solid #333', 'borderRadius': '4px', 'paddingTop': '6px', 'paddingBottom': '6px'}
                    ),
                ],
                className='d-flex align-items-center',
                style={'margin-top': '8px'},
            ), width=3,
        ),

        dbc.Col(
            html.Div([html.Button('?', id='info', style={'margin-right': '4px', 'margin-left': '4px', 'paddingLeft': '8px', 'paddingRight': '8px', 'border': '1px solid #333', 'borderRadius': '16px'})],
                style={'margin-top': '12px'}
            ), width=1,
        )

    ]),

    # Horizontal rule
    html.P(id='messages-stat', style={'fontSize': '12px', 'marginLeft': '8px','fontFamily': 'monospace'}),
    dcc.Store(id='all_messages'),
    dcc.Store(id='all_telegram_locations'),
    dcc.Store(id='messages'),  # TODO: check if faster if store the whole dataset
    dcc.Store(id='messages-dag-init'),
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
                    dcc.Loading(
                        html.Div([dag.AgGrid(id='messages-dag')], id='messages-feed', style={'height': '80vh', 'marginx': '8px'}), 
                        style={'height': '80vh', 'marginx': '8px'}
                    ),
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
                    style={'flex': 1, 'height': '83vh', 'backgroundColor': '#1f1f1f', 'borderRadius': '5px', 'padding': '10px'}),
            ], style=CARD_STYLE)
        ], width=3, style={'padding-right': '0px'}),

        # Right Column - Map and Sentiment Chart
        dbc.Col([
            dbc.Card([
                dcc.Loading(
                    html.Div(
                        children=dl.Map(
                            id='map', center=(33, 36), zoom=2,
                            children=[
                                dl.TileLayer(
                                    url='https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png',
                                    attribution='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>, &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors'),
                                    dl.LayersControl([
                                        dl.Overlay(dl.LayerGroup(id='telegram-layer'), name='Telegram', checked=True),
                                    ], id='lc', collapsed=False)
                            ],
                            style={'height': '100%', 'width': '100%'}),
                        id='div-map', 
                        style={'flex': 1, 'height': '50vh', 'backgroundColor': '#1f1f1f', 'borderRadius': '5px', 'padding': '0px', 'marginBottom': '10px'}),
                ),
                
                dcc.Loading(dcc.Graph(id='sentiment-chart', style={'height': '37vh'})),

                dcc.RadioItems(id='interval', options=[
                    {'label': '5min', 'value': '5min'},
                    {'label': '30min', 'value': '30min'},
                    {'label': '4h', 'value': '4h'},
                    {'label': '24h', 'value': '24h'}
                    ],
                    value='5min',
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

# --- Callbacks for the header ---

@app.callback(
    Output('date-input', 'value'),
    Input('datamap', 'value'),
    prevent_initial_call=False
)
def reset_date(map_name):
    """
    Reset the date to the initial date if the button 'reset' is clicked
    or if the map-database changes
    """

    if map_name:
        with open(os.path.join('./data/datamaps', map_name, 'datamap-config.yaml')) as f:
            map_config = yaml.safe_load(f)

        map_date_start = map_config['date']['start']
        map_date_start = datetime.strptime(map_date_start, '%Y-%m-%d %H:%M:%S')
        map_date_start = map_date_start.strftime('%Y-%m-%d %H:%M')

        return map_date_start

# --- Callbacks for the Telegram messages feed ---

@app.callback(
    Output('all_messages', 'data'),
    Input('datamap', 'value'),
    prevent_initial_call=False
)
def load_all_messages(datamap: Optional[str]):

    if datamap:
        tic = perf_counter()

        all_messages = []
        with open(os.path.join('./data/datamaps', datamap, 'telegram_gemini.jsonl'), 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    all_messages.append(record)
                except json.JSONDecodeError:
                    continue

        print(len(all_messages))

        # Add additional columns for rendering
        for idx, message in enumerate(all_messages):
            all_messages[idx]['message_html'] = render_message_html(message)
        logger.debug(f"Elapsed time for load_all_messages: {perf_counter() - tic:0.3f} sec")

        return all_messages
    return dash.no_update

@app.callback(
    Output('messages-stat', 'children'),
    Output('messages', 'data'),
    Input('datamap', 'value'),
    Input('date-input', 'value'),
    Input('all_messages', 'data'),
    prevent_initial_call=False
)
def load_messages(datamap: Optional[str], date_start: Optional[str], all_messages):


    if datamap and date_start:
        tic = perf_counter()

        # Filter dates
        date_start = datetime.strptime(date_start, '%Y-%m-%d %H:%M')

        date_start = date_start.strftime('%Y-%m-%d %H:%M')
        messages = [m for m in all_messages if date_start <= m['date']]
        messages_stat = f'Number of Telegram messages in map {datamap} after {date_start}: {len(messages)}'

        logger.debug(f"Elapsed time for load_messages: {perf_counter() - tic:0.3f} sec")

        return messages_stat, messages
    
    else:

        return dash.no_update, dash.no_update

@app.callback(
    Output('messages-feed', 'children', allow_duplicate=True), 
    Output('messages-dag-init', 'data'),
    Input('messages', 'data'), 
    prevent_initial_call=True
)
def create_grid(messages):
    
    tic = perf_counter()

    columnDefs = [
    {'field': 'message_html', 'cellRenderer': 'RenderHTML'},
    {'field': 'account', 'hide': True},  # Invisible column
    {'field': 'sim', 'hide': True},  # Invisible column
    {'field': 'date', 'hide': True},  # Invisible column
    {'field': 'text_english', 'hide': True}  # Invisible column
    ]

    grid = dag.AgGrid(
        id='messages-dag',
        columnDefs=columnDefs,
        rowData=messages[::-1],
        columnSize='responsiveSizeToFit',
        dashGridOptions={
            'headerHeight':0, 
            'rowStyle': {'border': 'none'},
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

    logger.debug(f"Elapsed time for create_grid: {perf_counter() - tic:0.3f} sec")

    return grid, grid

@app.callback(
    Output('messages-dag', 'filterModel'),
    Output('messages-dag', 'rowData', allow_duplicate=True),
    Output('reset-button', 'style'),
    Output('is_filtered', 'data'),
    Output('map', 'center', allow_duplicate=True),
    Output('map', 'zoom', allow_duplicate=True),
    Input('messages-dag', 'cellRendererData'),
    Input('is_filtered', 'data'),
    State('messages-dag', 'rowData'),
    State('all_messages', 'data'),
    prevent_initial_call=True
)
def update_grid(cellRendererData, is_filtered, current_row_data, all_messages):
    # FIXME: should use all_row_data

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
            message, date = all_messages[idx]['text_english'],  all_messages[idx]['date']
            query_message = f"[Date: {date}] {message}"
            logger.info(f"Search for similar message for idx {idx}, {date}")

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

@app.callback(
    Output('messages-feed', 'children'),
    Output('is_filtered', 'data', allow_duplicate=True),
    Output('reset-button', 'style', allow_duplicate=True),
    Input('reset-button', 'n_clicks'),
    State('messages-dag-init', 'data'),
    prevent_initial_call=True
)
def reset_grid(n_clicks, initial_grid):
    return initial_grid, False, {'width': '100%', 'border': 'none', 'borderRadius': '4px', 'margin-top': '8px', 'backgroundColor': 'grey'}

# --- Callbacks for the RAG system --

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

# --- Callbacks for the map ---

@app.callback(
    Output('map', 'center'),
    Output('map', 'zoom'),
    Input('datamap', 'value'),
    prevent_initial_call=False
    )
def view_map(datamap):

    if datamap:

        with open(os.path.join('./data/datamaps', datamap, 'datamap-config.yaml')) as f:
            config = yaml.safe_load(f)
            lat = config['map']['lat']
            lon = config['map']['lon']
            zoom = config['map']['zoom']

        logger.info(f"Recenter map at ({lat}, {lon}) with zoom={zoom}")

        return (lat, lon), zoom

    return dash.no_update, dash.no_update
    

@app.callback(
    Output('all_telegram_locations', 'data'),
    Input('all_messages', 'data'),
    prevent_initial_call=True
)
def load_telegram_locations(all_messages):

    logger.info('Load Telegram all locations')
    
    if all_messages:
        return get_telegram_locations(all_messages)
    return []

@app.callback(
    Output('telegram-layer', 'children'),
    Input('date-input', 'value'),
    Input('all_telegram_locations', 'data'),
    prevent_initial_call=True
)
def update_telegram_markers(date_start, all_telegram_locations):

    if date_start:

        filtered_telegram_locs = [
            dl.Marker(
                position=item["position"],
                children=[dl.Tooltip(item['tooltip']), dl.Popup(item['popup'])],
                icon = dict(iconUrl='assets/marker-icon-blue.png', iconAnchor=(12, 18))
            )
            for item in all_telegram_locations if date_start <= item["date"]
        ]

        return filtered_telegram_locs
    
    return dash.no_update, dash.no_update

# --- Callbacks for the sentiment chart ---

@app.callback(
    Output('sentiment-chart', 'figure'),
    Input('messages', 'data'),
    Input('interval', 'value'),
    prevent_initial_call=True
)
def update_sentiment_chart(messages, interval):
    tic = perf_counter()
    chart = generate_chart(messages, interval)
    logger.debug(f"Elapsed time for chart: {perf_counter() - tic:0.3f} sec")
    return chart

    # TODO: Patch()

# --- Main function ---

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

    app.run_server(debug=False)


if __name__ == '__main__':

    main()

# uv run liveapp.py --no-server