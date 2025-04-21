import os
import requests
import json
import folium
import numpy as np
import gradio as gr
import pandas as pd
from loguru import logger


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


with open("./data/data_telegram_250331.json", 'r', encoding='utf-8') as file:
    messages = json.load(file)
#messages = messages[:20]  # Limit to 100 messages for performance


# Function to convert sentiment score to a color using RdYlGn colormap
def sentiment_to_color(negative_score, neutral_score, positive_score):

    if neutral_score > max(negative_score, positive_score):
            return "rgba(255, 255, 255, 1.0)"  # White neutral sentiment
    else:
        return f"rgba({int(negative_score*255)}, {int(positive_score*255)}, 0.0, 1.0)"


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


# JavaScript function to handle zoom
# js_code = """
# function zoomToCoordinates(lat, lon) {
#     var map = window.map;
#     if (map) {
#         map.setView([lat, lon], 5);
#     }
# }

# document.addEventListener('DOMContentLoaded', function() {
#     var mapElement = document.querySelector('.folium-map');
#     if (mapElement) {
#         window.map = L.map(mapElement.id).setView([35.0, 38.0], 7);
#         L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
#             attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
#         }).addTo(window.map);
#     }
# });
# """

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
with gr.Blocks(theme=gr.themes.Ocean()) as demo:
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

            gr.Textbox("", interactive=True, label="Input Text", placeholder="Enter your text here...")
            #gr.Checkbox(label="Use Google Search", value=False, interactive=True) 
            submit_button = gr.Button("Run")

            response_ai = """On March 31, 2025, several Telegram accounts reported bombings and shelling in and around Rafah. Here's a summary of the events as they unfolded, according to the posts:\n\n*   **Early Morning (00:49 - 02:24):** Reports indicate building demolition and artillery shelling west of Rafah (hamza20300). An explosion was reported in the Tel Sultan neighborhood of Rafah (hpress at 02:20), followed shortly by reports of a residential square being blown up in Al-Sultan neighborhood, west of Rafah (hamza20300 at 02:24).\n\n*   **Daytime (12:28 - 17:16):** There are reports of displacement of Rafah residents (Nuseirat1 at 12:28, hamza20300 at 15:45). Leaflets with evacuation orders were dropped by aircraft over Rafah (hamza20300 at 12:33). Later in the afternoon, a young man was reportedly killed, and his brother injured, in a targeted attack on their vehicle while they were working in transportation from Rafah (hamza20300 at 17:16, mohnadQ at 17:15).\n\n*   **Evening (19:33 - 21:00):** Reports of artillery shelling and heavy explosions north of Rafah (ramreports at 19:46, mohnadQ at 19:33, QudsN at 19:34). Shelling was described as intense and continuous in the northeastern areas of Rafah (hamza20300 at 19:52). Explosions were heard between Khan Yunis and Rafah (Nuseirat1 at 19:36). Illumination bombs were dropped east of Rafah (mohnadQ at 20:50, hamza20300 at 21:00).\n\n*   **Late Night (23:45 - 23:47):** Bombing operations were reported in the western areas of Rafah (ramreports at 23:45). Residential buildings in the Tel Sultan neighborhood were reportedly blown up (hamza20300 at 23:47).\n
            """
            response = gr.HTML(gr.Markdown(response_ai, max_height=750))

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


if __name__ == "__main__":
    demo.launch()