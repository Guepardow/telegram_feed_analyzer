import os
import yaml
import json
import folium
import chromadb
import requests
import numpy as np
import gradio as gr
import pandas as pd
from loguru import logger
from google import genai
from google.genai import types

from src.gemini.build_rag_db import GeminiEmbeddingFunction


# Read the JSON file
if not os.path.exists("./data/data_telegram_250331.json"):
    # URL of the file to download
    url = 'https://mehdimiah.com/blog/telegram_feed_analyzer/data/data_telegram_250331.json'

    # Specify the target directory and file path
    file_path = "./data/data_telegram_250331.json"

    # Ensure the target directory exists
    os.makedirs('./data', exist_ok=True)

    # Send a GET request to the URL and write the content to the specified file path
    with open(file_path, 'wb') as file:
        file.write(requests.get(url).content)

    logger.success(f'File downloaded and saved to {file_path}')


# Load the JSON data with enhanced Telegram messages
with open("./data/data_telegram_250331.json", 'r', encoding='utf-8') as file:
    messages = json.load(file)


# Function to convert sentiment score to a color using RdYlGn colormap
def sentiment_to_color(negative_score, neutral_score, positive_score):

    if neutral_score > max(negative_score, positive_score):
            return "rgba(255, 255, 255, 1.0)"  # White neutral sentiment
    else:
        return f"rgba({int(negative_score*255)}, {int(positive_score*255)}, 0.0, 1.0)"


# JavaScript function to handle zoom
js_code = """
function zoomToCoordinates(lat, lon) {
    var map = window.map;
    if (map) {
        map.setView([lat, lon], 5);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    var mapElement = document.querySelector('.folium-map');
    if (mapElement) {
        window.map = L.map(mapElement.id).setView([35.0, 38.0], 7);
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
        }).addTo(window.map);
    }
});
"""

# Function to generate message feed
def generate_message_feed(language):

    feed = ""
    location_markers = []
    urls = []
    texts = []

    for i, message in enumerate(messages, start=1):

        url = f"https://t.me/{message['account']}/{message['id']}"
        border_color = sentiment_to_color(float(message['negative_genai']), float(message['neutral_genai']), float(message['positive_genai']))

        feed += f"<div style='background-color: #242424; border-left: 5px solid {border_color}; padding: 15px; margin-bottom: 10px; border-radius: 5px; box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.1); width: 425px;'>"
        feed += f"""
                <div style="display: flex; justify-content: space-between;">
                    <span><a href='{url}' target='_blank'>{url}</a><br></span>
                    <span>{message['date']}</span>
                </div>
                """

        if language == 'English':
            feed += f"{message['text_english_genai']}<br>"
        elif language == 'No translation':
            feed += f"{message['text']}<br>"
        for coords in message['coords_genai']:
            if coords[0] is not None and coords[1] is not None:

                # NB: add a random noise to avoid overlapping of markers
                location_markers.append((coords[0] + np.random.uniform(-1e-4, 1e-4), coords[1] + np.random.uniform(-1e-4, 1e-4)))
                urls.append(url)
                texts.append(message['text_english_genai'])

        # == Add icons at the bottom of the message ==
        feed += """<div style="display: flex; justify-content: space-between; align-items: center;">"""

        # Icons for geolocation
        feed += """<div style="display: flex; align-items: center;">"""
        for coords, loc in zip(message['coords_genai'], message['geolocs_genai']):
            if coords[0] is not None and coords[1] is not None:
                feed += f"""
                        <div class="icon-container" style="display: inline-flex; align-items: center;">
                            <img src='https://mehdimiah.com/blog/telegram_feed_analyzer/icon/location_r.png' width='16' 
                                style='margin-right: 5px; cursor: pointer;'
                                title="{loc}"
                                onclick="zoomToCoordinates({coords[0]}, {coords[1]})"
                            >
                        </div>
                        """

        # Add icons for photo and video
        if message['has_photo']:
            feed += """
                    <div class="icon-container" style="display: inline-flex; align-items: center;">
                        <img src='https://mehdimiah.com/blog/telegram_feed_analyzer/icon/photo_r.png' width='16' 
                            style='margin-right: 5px;'
                        >
                    </div>
                    """
        if message['has_video']:
            feed += """
                    <div class="icon-container" style="display: inline-flex; align-items: center;">
                        <img src='https://mehdimiah.com/blog/telegram_feed_analyzer/icon/film_r.png' width='16' 
                            style='margin-right: 5px;'
                        >
                    </div>
                    """

        feed += "</div>"  # end of the icons line on the left
        
         # Add icon for similarity search
        feed += """
                <div class="icon-container" style="display: inline-flex; align-items: right;">
                    <img src='https://mehdimiah.com/blog/telegram_feed_analyzer/icon/similar_r.png' width='16' 
                        style='margin-left: 5px; cursor: pointer;
                        onclick="updateMessageFeed()'
                    >
                </div>
                """
        
        feed += "</div>"  # end of the icons line
        feed += "</div>"  # end of the message
        
    return feed, location_markers, urls, texts


# Initalize the Google GenAI client
GOOGLE_API_KEY = yaml.safe_load(open("config.yaml"))['secret_keys']['google']['api_key']
genai_client = genai.Client(api_key=GOOGLE_API_KEY)

# Import the embedding function
embed_function = GeminiEmbeddingFunction(genai_client=genai_client, document_mode=False)

# Initialize the HttpClient to connect to the Chroma server
chroma_client = chromadb.HttpClient(host='localhost', port=8001)
database = chroma_client.get_collection(name="telegram", embedding_function=embed_function)

# Function to answer the question using the database (RAG)
def question_to_database(query):
    """
    Question-answering function using Gemini
    :param query: the question of the user.
    :param database: the Chroma database with the embeddings of documents.
    :param embed_function: the function used to embed the query
    """
    query_str = query.value if isinstance(query, gr.Textbox) else query

    result = database.query(query_texts=[query_str], n_results=20)  # Here 20 documents is 1% of the total database
    [all_passages] = result["documents"]

    query_oneline = query_str.replace("\n", " ")
    
    # Prompt to answer the question   
    prompt = f"""You are a knowledgeable and professional journalism bot specializing in fact-checking and international humanitarian law.
    You answer questions using text from the reference passage included below. Be sure to respond in complete sentences, providing comprehensive and well-researched information.
    Adopt a journalistic tone.
    
    Since the data come from Telegram, be cautious, as it is from a social network and the information can be inaccurate.
    Each passage corresponds to a Telegram post: the content, the account and the date of the post are mentioned in each passage. 
    Keep in mind that several hours may pass between an event and the publication of a message related to it. 
    
    If the passage is irrelevant to the answer, you may ignore it.
    
    QUESTION: {query_oneline}

    """
    
    # Add the retrieved documents to the prompt.
    for passage in all_passages:
        passage_oneline = passage.replace("\n", " ")
        prompt += f"PASSAGE: {passage_oneline}\n"

    # Answer with Gemini with low creativity
    answer = genai_client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt, 
        config=types.GenerateContentConfig(temperature=0.1)
    )

    return answer.text


# Function to generate map
def generate_map(location_markers, urls, texts):
    m = folium.Map(location=[35.0, 38.0], tiles="Cartodb Dark Matter", zoom_start=7, height='100%', width='100%', padding=0)
    for coords, url, text in zip(location_markers, urls, texts):

        tooltip_html= f'<div style="white-space: normal">{text}</div>'

        folium.Marker(
            location=coords, 
            tooltip=folium.map.Tooltip(folium.Html(tooltip_html, script=True, width=300).render()), 
            popup=f"<a href='{url}' target='_blank'>{url}</a>"
            ).add_to(m)
    return m._repr_html_()


# Function to generate bar chart
def generate_chart(interval):

    df = pd.DataFrame(messages)
    df["date"] = pd.to_datetime(df["date"])
    df['date_r'] = df['date'].dt.round(interval)
    df['date_r'] = df['date_r'] + pd.Timedelta(hours=4)

    # Determine the majority sentiment for each post
    df['dominant_sentiment'] = df[['negative_genai', 'neutral_genai', 'positive_genai']].idxmax(axis=1)

    # Group by the selected interval and count the number of posts for each sentiment
    grouped = df.groupby(['date_r', 'dominant_sentiment']).size().unstack(fill_value=0)
    grouped = grouped.reset_index(drop=False)
    df_long = pd.melt(grouped, id_vars=['date_r'], var_name='sentiment', value_name='count').sort_values(by='sentiment', ascending=False)

    df_long['sentiment'] = df_long['sentiment'].replace({
        'negative_genai': 'negative',
        'neutral_genai': 'neutral',
        'positive_genai': 'positive'
    })

    return df_long


# Gradio interface
with gr.Blocks(theme=gr.themes.Ocean(), js=js_code) as demo:
    gr.Markdown("# AI-Augmented Telegram Feed Analyzer")

    with gr.Row():
        with gr.Column(scale=1):
            language = gr.Dropdown(choices=['English', 'No translation'], label="Select Translation Option", interactive=True)

            gr.Markdown("## Message Feed")
            message_feed, location_markers, urls, texts = generate_message_feed(language.value)
            feed = gr.HTML(message_feed, max_height=730)
            language.change(fn=lambda language: generate_message_feed(language)[0],  # Only update the message_feed part
                            inputs=language, outputs=feed)

            reset_button = gr.Button("Reset Filters")

        with gr.Column(scale=1):

            query = gr.Textbox("", interactive=True, label="Input Text", placeholder="Enter your question here...")
            #gr.Checkbox(label="Use Google Search", value=False, interactive=True) 
            submit_button = gr.Button("Run")

            response = gr.HTML(gr.Markdown(question_to_database(query) if query.value else "", max_height=750))

        with gr.Column(scale=2):

            # Map
            map_component = gr.HTML(generate_map(location_markers, urls, texts), max_height=550, padding=False, container=True)

            # JavaScript component to include the zoom function
            # js_component = gr.HTML(f"""
            # <script>
            # {js_code}
            # </script>
            # """)

            # Chart
            interval=gr.Radio(["5min", "30min", "4h", "24h"], label="Select Time Interval", value="4h", interactive=True)

            df_sentiment_time = generate_chart(interval=interval.value)
            chart_sentiment_time = gr.BarPlot(df_sentiment_time, x="date_r", y="count", color="sentiment", x_title='Time', y_title='Number of messages', title="Evolution of sentiment in messages", color_map={"neutral": "lightgrey","negative": "red",  "positive": "green"})
            interval.change(fn=generate_chart, inputs=interval, outputs=chart_sentiment_time)


    # reset_button.click(lambda: ("English", datetime(2024, 11, 20).timestamp()), None, [language, date_slider])
    submit_button.click(question_to_database, inputs=query, outputs=response)

if __name__ == "__main__":
    demo.launch()

# terminal 1 to run the database server : uv run chroma run --path ./data/.chromadb/rag_db
# terminal 2 to run the gradio dashboard : uv run gradio app.py