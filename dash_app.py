import os
import json
import yaml
import folium
import requests
import numpy as np
import pandas as pd

import dash
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.express as px
from dash_extensions.enrich import DashProxy, TriggerTransform

from src.gemini.build_rag_db import GeminiEmbeddingFunction
import chromadb
from google import genai
from google.genai import types


# Load data
DATA_PATH = "./data/data_telegram_250331.json"
if not os.path.exists(DATA_PATH):
    url = 'https://mehdimiah.com/blog/telegram_feed_analyzer/data/data_telegram_250331.json'
    os.makedirs('./data', exist_ok=True)
    with open(DATA_PATH, 'wb') as f:
        f.write(requests.get(url).content)

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    messages = json.load(f)[:200]

# Load config and initialize GenAI
GOOGLE_API_KEY = yaml.safe_load(open("config.yaml"))['secret_keys']['google']['api_key']
genai_client = genai.Client(api_key=GOOGLE_API_KEY)
embed_function = GeminiEmbeddingFunction(genai_client=genai_client, document_mode=False)

chroma_client = chromadb.HttpClient(host='localhost', port=8000)
database = chroma_client.get_collection(name="telegram", embedding_function=embed_function)

# Utility functions
def sentiment_to_color(neg, neu, pos):
    if neu > max(neg, pos):
        return "rgba(255,255,255,1.0)"
    return f"rgba({int(neg*255)}, {int(pos*255)}, 0, 1.0)"
            
# Function to generate message feed
def generate_feed(language, account_name=None):

    cards = []
    filtered_messages = messages if account_name is None else [msg for msg in messages if msg['account'] == account_name]

    for i, message in enumerate(filtered_messages):
        url = f"https://t.me/{message['account']}/{message['id']}"
        border_color = sentiment_to_color(float(message['negative_genai']), float(message['neutral_genai']), float(message['positive_genai']))
        content = message['text_english_genai'] if language == 'English' else message['text']

        user_icon_style = {"marginRight": "5px", "cursor": "pointer"} if account_name is None else {"marginRight": "5px", "cursor": "not-allowed", "opacity": "0.5"}

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
                                dbc.Tooltip(geoloc, target=f"location-icon-{i}-loc{j}", placement="top"),
                                html.Img(src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/location_r.png", height=16, style={"marginRight": "5px"}, id=f"location-icon-{i}-loc{j}") if message['coords_genai'] else None
                                ])
                                for j, geoloc in enumerate(message['geolocs_genai'])
                        ], style={"display": "flex", "alignItems": "center", "marginLeft": "auto"}),
                        html.Img(src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/photo_r.png", height=16, style={"marginRight": 5}) if message['has_photo'] else None,
                        html.Img(src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/film_r.png", height=16) if message['has_video'] else None
                        ], style={"display": "flex", "alignItems": "center"}),
                    html.Div([
                        html.Img(src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/similar_r.png", height=16)
                    ], style={"display": "flex", "alignItems": "center", "marginLeft": "auto"})
                ], style={"display": "flex", "gap": "5px"})
            ], style={"backgroundColor": "#353535", "borderLeft": f"5px solid {border_color}", "padding": 15, "marginBottom": 10, "marginRight": 10, "borderRadius": 5, "color": "white"})
        ]))

    return cards

def generate_map(messages):

    m = folium.Map(location=[35.0, 38.0], tiles="Cartodb Dark Matter", zoom_start=7)
    location_markers = []
    urls = []  
    texts = []
    accounts = []
    dates = []

    for i, message in enumerate(messages):
        coords = [c for c in message['coords_genai'] if c[0] is not None and c[1] is not None]
        url = f"https://t.me/{message['account']}/{message['id']}"

        for coord in coords:
            location_markers.append((coord[0] + np.random.uniform(-1e-4, 1e-4), coord[1] + np.random.uniform(-1e-4, 1e-4)))
            urls.append(url)
            texts.append(message['text_english_genai'])
            accounts.append(message['account'])
            dates.append(message['date'])

    for coords, url, text, account, date in zip(location_markers, urls, texts, accounts, dates):
        # tooltip_html = f'<div style="white-space: normal">{text}</div>'
        tooltip_html = f'''
        <div style="white-space: normal; background-color: #353535; color: white">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="float: left;padding-left:3px">{account}</span>
                <span style="float: right;padding-right:3px">{date}</span>
            </div>
            <div style="margin-top: 2px;padding:3px">{text}</div>
        </div>
        '''
        folium.Marker(
            location=coords,
            tooltip=folium.map.Tooltip(folium.Html(tooltip_html, script=True, width=300).render()),
            popup=f"<a href='{url}' target='_blank'>{url}</a>"
        ).add_to(m)

    return m._repr_html_()


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

    # Title
    fig.update_layout()

    return fig


def question_to_database(query):
    result = database.query(query_texts=[query], n_results=20)
    [all_passages] = result["documents"]
    query_oneline = query.replace("\n", " ")
    prompt = f"""
    You are a knowledgeable and professional journalism bot specializing in fact-checking and international humanitarian law.
    You answer questions using text from the reference passage included below. Be sure to respond in complete sentences, providing comprehensive and well-researched information.
    Adopt a journalistic tone.

    Since the data come from Telegram, be cautious, as it is from a social network and the information can be inaccurate.
    Each passage corresponds to a Telegram post: the content, the account and the date of the post are mentioned in each passage.
    Keep in mind that several hours may pass between an event and the publication of a message related to it.

    If the passage is irrelevant to the answer, you may ignore it.

    QUESTION: {query_oneline}
    """
    for passage in all_passages:
        passage_oneline = passage.replace("\n", " ")
        prompt += f"PASSAGE: {passage_oneline}\n"

    answer = genai_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1)
    )
    return answer.text

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
            dcc.Store(id="filter-state", data={"account_name": None}),
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
            html.Iframe(id="map-box", srcDoc=generate_map(messages), style={"height": "70%", "width": "100%"}),
            html.Div([
                dcc.RadioItems(["5min", "30min", "4h", "24h"], "4h", id="interval", inline=False, style={"flex": "1", "marginTop": 100}),
                dcc.Graph(id="sentiment-chart", figure=generate_chart("4h"), style={"flex": "7"})
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
    answer = question_to_database(query)
    return html.Div([html.Hr(), html.Pre(answer, style={"whiteSpace": "pre-wrap"})])

@app.callback(
    Output("sentiment-chart", "figure"),
    Input("interval", "value")
)
def update_sentiment_chart(interval):
    return generate_chart(interval)

# Combined callback to handle both language change and user icon click
@app.callback(
    Output("message-feed", "children"),
    Output("filter-state", "data"),
    Output("reset-button", "style"),
    Input("language", "value"),
    Input({"type": "user-icon", "index": dash.dependencies.ALL}, "n_clicks"),
    Input("reset-button", "n_clicks"),
    State("filter-state", "data"),
    prevent_initial_call=True
)
def update_message_feed(language, n_clicks_user, n_clicks_reset, filter_state):
    ctx = callback_context

    if not ctx.triggered:
        return generate_feed(language=language), filter_state, {"display": "none"}

    triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if "user-icon" in triggered_id:
        clicked_index = eval(triggered_id)['index']
        filtered_account = messages[clicked_index]['account']
        filter_state["account_name"] = filtered_account
        return generate_feed(language=language, account_name=filtered_account), filter_state, {"display": "block", 'width': '100%', 'backgroundColor': '#343a40', 'color': '#ffffff', 'border': 'none', 
        'padding': '10px','borderRadius': '12px','fontSize': '16px', "marginTop": 15}

    elif "reset-button" in triggered_id:
        filter_state["account_name"] = None
        return generate_feed(language=language), filter_state, {"display": "none"}

    return generate_feed(language=language, account_name=filter_state["account_name"]), filter_state, {"display": "none"}


if __name__ == '__main__':
    app.run(debug=True)
