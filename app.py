import json
import yaml
import numpy as np
import pandas as pd
import dash_leaflet as dl

import dash
import plotly.express as px
import dash_bootstrap_components as dbc
from dash_extensions.enrich import DashProxy, TriggerTransform

from dash import html, dcc, Input, Output, State, callback_context

from src.rag import RAG
from src.similarity_search import SimilaritySearch


# Load data
with open("./data/data_telegram_250331.json", 'r', encoding='utf-8') as f:
    messages = json.load(f)

# Load config and initialize the RAG system and the SimilaritySearch system
with open("./config.yaml") as f:
    config = yaml.safe_load(f)
    GOOGLE_API_KEY = config['secret_keys']['google']['api_key']

similarity_search = SimilaritySearch(GOOGLE_API_KEY=GOOGLE_API_KEY)
similarity_search.load_collection(host='localhost', port=8000)

rag = RAG(GOOGLE_API_KEY=GOOGLE_API_KEY)
rag.load_collection(host='localhost', port=8001)

# Utility functions
def sentiment_to_color(neg, neu, pos):
    if neu > max(neg, pos):
        return "rgba(255,255,255,1.0)"
    return f"rgba({int(neg*255)}, {int(pos*255)}, 0, 1.0)"
            
# Function to generate message feed
def generate_feed(language, account_name=None, similarity_order=None):

    cards = []
    is_using_a_filter = (account_name is not None) or (similarity_order is not None)

    # Filter messages based on the account name if provided
    filtered_messages = messages if (account_name is None) else [msg for msg in messages if msg['account'] == account_name]

    # If similarity_order is provided, sort the messages based on that order
    if similarity_order:
        filtered_messages = [filtered_messages[i] for i in similarity_order]

    user_icon_style = {"marginRight": "5px", "cursor": "not-allowed", "opacity": "0.5"} if is_using_a_filter else {"marginRight": "5px", "cursor": "pointer"}
    similar_icon_style = {"marginLeft": "auto", "cursor": "not-allowed", "opacity": "0.5", "display": "flex","alignItems": "center"} if is_using_a_filter else {"display": "flex", "alignItems": "center", "marginLeft": "auto", "cursor": "pointer"}
                  # {"display": "flex", "alignItems": "center", "marginLeft": "auto"}

    for i, message in enumerate(filtered_messages):
        url = f"https://t.me/{message['account']}/{message['id']}"
        border_color = sentiment_to_color(float(message['negative_genai']), float(message['neutral_genai']), float(message['positive_genai']))
        content = message['text_english_genai'] if language == 'English' else message['text']
        background_color = "#555555" if i == 0 and similarity_order else "#353535"

        cards.append(html.Div([
            html.Div([
                html.Div([
                    html.Div([
                        html.Img(src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/user_r.png", height=16, style=user_icon_style,
                                id={"type": "user-icon", "index": i}),
                        html.Span(message['account'], style={"float": "left", "verticalAlign": "top"})
                        ], style={"display": "flex", "alignItems": "center"}),
                    html.Div([
                        html.A([
                            html.Img(src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/link_r.png", height=16, style={"marginRight": 5}),
                            ], href=url, target="_blank"),
                        html.Span(message['date'], style={"float": "right"})
                    ], style={"display": "flex", "alignItems": "center", "marginLeft": "auto"})
                ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),
                html.Div(content, style={"marginTop": 5, "marginBottom": 5}),
                html.Div([
                    html.Div([
                        html.Div([
                            html.Div([
                                # NB: 10*i+j where i is the index of the message and j is the index of the geolocation
                                #  Since j is never greater than 9, we can use it as a unique identifier
                                dbc.Tooltip(geoloc, target={"type": "location-icon", "index": 10*i+j}, placement="top"),
                                html.Img(src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/location_r.png", height=16, style={"marginRight": "5px"}, id={"type": "location-icon", "index": 10*i+j}) if message['coords_genai'] else None
                                ])
                                for j, geoloc in enumerate(message['geolocs_genai'])
                        ], style={"display": "flex", "alignItems": "center", "marginLeft": "auto"}),
                        html.Img(src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/photo_r.png", height=16, style={"marginRight": 5}) if message['has_photo'] else None,
                        html.Img(src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/film_r.png", height=16) if message['has_video'] else None
                        ], style={"display": "flex", "alignItems": "center"}),
                    html.Div([
                        html.Img(src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/similar_r.png", height=16, id={"type": "similar-icon", "index": i})
                    ], style=similar_icon_style)
                ], style={"display": "flex", "gap": "5px"})
            ], style={"backgroundColor": background_color, "borderLeft": f"5px solid {border_color}", "padding": 15, "marginBottom": 10, "marginRight": 10, "borderRadius": 5, "color": "white"})
        ]))

    return cards

def get_geolocations(messages: list[dict]) -> list[dict]:
    geolocations = []
    for mid, message in enumerate(messages):
        for gid, coords in enumerate(message['coords_genai']):
            geolocations.append({'mid': mid, 'gid': gid, 'coords': coords})

    return geolocations


def generate_map(messages):

    locations = []
    for message in messages:
        coords = [c for c in message['coords_genai']]
        url = f"https://t.me/{message['account']}/{message['id']}"

        account, date = message['account'], message['date']
        text = message['text_english_genai']

        for coord in coords:

            tooltip = html.Div([
                html.Div([
                    html.Span(account, style={"float": "left", "paddingLeft": "3px"}),
                    html.Span(date, style={"float": "right", "paddingRight": "3px"})
                ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center"}),
                html.Div(text, style={"marginTop": "2px", "padding": "3px"})
            ], style={"whiteSpace": "normal", "backgroundColor": "#353535", "color": "white", "width": "300px"})            

            locations.append({'lat': coord[0]+ np.random.uniform(-1e-4, 1e-4), 'lon': coord[1]+ np.random.uniform(-1e-4, 1e-4),  # Add noise to avoid overlapping markers
            'tooltip': tooltip, 'popup': html.A(url, href=url, target="_blank")})

    m =  dl.Map(center=(32, 35), zoom=8, children=[
        dl.TileLayer(url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
                     attribution="© OpenStreetMap contributors, © CartoDB"),
        *[dl.Marker(position=(loc["lat"], loc["lon"]),
                    children=[
                        dl.Tooltip(loc["tooltip"]),
                        dl.Popup(loc["popup"])
                    ]) for loc in locations]
    ], style={'width': '100%', 'height': '100%'})

    return m

def generate_chart(interval):

    df = pd.DataFrame(messages)
    df["date"] = pd.to_datetime(df["date"])
    df['date_r'] = df['date'].dt.round(interval)

    df['dominant_sentiment'] = df[['negative_genai', 'neutral_genai', 'positive_genai']].idxmax(axis=1)

    grouped = df.groupby(['date_r', 'dominant_sentiment']).size().unstack(fill_value=0).reset_index()
    df_long = pd.melt(grouped, id_vars=['date_r'], var_name='sentiment', value_name='count')

    df_long['sentiment'] = df_long['sentiment'].replace({
        'negative_genai': 'negative',
        'neutral_genai': 'neutral',
        'positive_genai': 'positive'
    })

    fig = px.bar(df_long, x='date_r', y='count', color='sentiment',
                 color_discrete_map={"neutral": "#eeeeee", "negative": "#e74c3c", "positive": "#2ecc71"},
                 labels={'date_r': '', 'count': 'Number of messages'})

    # Update the layout for dark background
    fig.update_layout(
        plot_bgcolor='#222222',  
        paper_bgcolor='#222222',
        font=dict(color='white'),
        yaxis=dict(gridcolor='gray'),
        title_text="Evolution of dominant sentiment", 
        title_x=0.5,
    )

    return fig


# Initialize app
app = DashProxy(__name__, external_stylesheets=[dbc.themes.DARKLY], transforms=[TriggerTransform()])
app.title = "Telegram Feed Analyzer"

app.layout = dbc.Container([
    html.H4("AI-Augmented Telegram Feed Analyzer", style={'font-family': 'IBM Plex Sans, sans-serif',
                                                          'padding-top': '20px'}),
    dbc.Row([
        dbc.Col([
            dbc.Row([
                html.H5("Language:", style={"width": '30%'}),
                dcc.Dropdown(options=["English", "No translation"], value="English", id="language", clearable=False, style={"width": "65%"})
            ]),
            html.Div(id="message-feed", children=generate_feed("English"), style={"maxHeight": "730px", "overflowY": "scroll", "marginTop": 20}),
            dcc.Store(id="filter-state", data={"account_name": None, "similarity_order": None}),
            html.Button("Reset", id="reset-button", n_clicks=0, style={"display": "none"})
        ], width=3),

        dbc.Col([
            dbc.Row([
                dcc.Textarea(id="query-box", placeholder="Enter your question here...", style={"width": "85%", "height": 120, 'backgroundColor': '#343a40', 'color': '#ffffff', 'borderRadius': '12px', "minHeight": 40}),
                html.Button("Run", id="run-btn", style={'width': '10%', 'backgroundColor': '#343a40', 'color': '#ffffff', 'border': 'none',
                'padding': '10px','borderRadius': '12px','fontSize': '16px', "marginLeft": 5}),
            ]),
            html.Div(id="response-box", style={"marginTop": 20})
        ], width=3, style={"padding-right": 0}),

        dbc.Col([
            html.Div(id="map-box", children=generate_map(messages), style={"height": "80%"}),
            html.Div([
                dcc.RadioItems(["5min", "30min", "4h", "24h"], "30min", id="interval", inline=False, style={"flex": "1", "marginTop": 100}),
                dcc.Graph(id="sentiment-chart", figure=generate_chart("30min"), style={"flex": "7"})
            ], style={"display": "flex", "height": "40%"})
        ], width=6, style={"padding-left": 0})

    ])
], fluid=True)

@app.callback(
    Output("response-box", "children"),
    Input("run-btn", "n_clicks"),
    State("query-box", "value"),
    prevent_initial_call=True
)
def run_query(n_clicks, query):
    if not query:
        return "Please enter a query."
    answer = rag.query(query=query, n_results=20)
    return html.Div([html.Hr(), html.Pre(answer, style={"whiteSpace": "pre-wrap"})])

@app.callback(
    Output("sentiment-chart", "figure"),
    Input("interval", "value")
)
def update_sentiment_chart(interval):
    return generate_chart(interval)

# Combined callback to handle language change, user icon click, and similar icon click
@app.callback(
    Output("message-feed", "children"),
    Output("reset-button", "style"),
    Input("language", "value"),
    Input({"type": "user-icon", "index": dash.dependencies.ALL}, "n_clicks"),
    Input({"type": "similar-icon", "index": dash.dependencies.ALL}, "n_clicks"),
    Input("reset-button", "n_clicks"),
    prevent_initial_call=True
)
def update_message_feed(language, n_clicks_user, n_clicks_similar, n_clicks_reset):
    ctx = callback_context

    if not ctx.triggered:
        return generate_feed(language=language), {"display": "none"}

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if "user-icon" in triggered_id:
        clicked_index = eval(triggered_id)['index']
        filtered_account = messages[clicked_index]['account']
        return generate_feed(language=language, account_name=filtered_account), {"display": "block", 'width': '100%', 'backgroundColor': '#343a40', 'color': '#ffffff', 'border': 'none',
        'padding': '10px','borderRadius': '12px','fontSize': '16px', "marginTop": 15}

    elif "similar-icon" in triggered_id:
        clicked_index = eval(triggered_id)['index']
        clicked_text, clicked_date = messages[clicked_index]['text_english_genai'], messages[clicked_index]['date']
        query_message = f"[Date: {clicked_date}] {clicked_text}"  # Format the document

        results = similarity_search.query(query_message, n_results=100)  # top 100 most similar messages
        similarity_order = [int(mid) for mid in results['ids'][0]]
        return generate_feed(language=language, similarity_order=similarity_order), {"display": "block", 'width': '100%', 'backgroundColor': '#343a40', 'color': '#ffffff', 'border': 'none',
        'padding': '10px','borderRadius': '12px','fontSize': '16px', "marginTop": 15}

    elif "reset-button" in triggered_id:
        return generate_feed(language=language), {"display": "none"}

    else:
        raise NotImplementedError(f"This callback is not implemented for the triggered ID: {triggered_id}")



if __name__ == '__main__':
    app.run(debug=True)

# uv run app.py