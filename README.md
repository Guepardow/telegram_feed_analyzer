# Telegram Feed Analyzer

<p align="center">
    <img src="https://www.mehdimiah.com/blog/telegram_feed_analyzer/main_400p.png" alt="Headline image" width="600"/><br>Some cases where journalists face difficulties accessing the field: war,  natural disasters or military restrictions.
</p>

<p align="center">
    <img src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/youtube.png" alt="YouTube" width="20px">
    <a href="https://www.youtube.com/watch?v=oqyiQ377ngA">YouTube Video</a>
    <img src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/kaggle.png" alt="Kaggle" width="20px" style="vertical-align: middle;margin-left:40px">
    <a href="https://www.kaggle.com/code/guepardow/telegram-feed-analyzer">Kaggle Notebook</a>
    <img src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/blog.png" alt="Blog" width="20px" style="vertical-align: middle;margin-left:40px">
    <a href="https://mehdimiah.com/blog/telegram_feed_analyzer">Blog post</a>
</p>

This project enhances Telegram feeds, using the Gemini AI API, by adding the following capabilities:
- 🗺️ translation to English
- 📍 geolocation
- 😳 sentiment analysis
- ✉️ similar message search
- ❓ retrieval-augmented generation (RAG)

📆 **News**:
- *20-04-2024: this project was developed for the Kaggle competition [5-day Gen AI Intensive Course with Google](https://www.kaggle.com/competitions/gen-ai-intensive-course-capstone-2025q1).*

# Installation

This project uses `uv` as a project manager; you can [download it here](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/Guepardow/telegram_feed_analyzer
cd telegram_feed_analyzer
uv sync
```

You can get a GOOGLE API KEY [here](https://aistudio.google.com/app/apikey).

# Data

You can download 1987 "enhanced messages" posted on Telegram on March 31st, 2025 about the situation in Israel and Palestine:

```sh
wget -q https://mehdimiah.com/blog/telegram_feed_analyzer/data/data_telegram_250331.json -O ./data/telegram_250331.json
```

# Gradio Dashboard

First, create a Persistent Chroma database for the RAG system (the database with embeddings will be stored in `./data/.chromadb/rag_db`):
```sh
cd src/gemini
uv run build_rag_db.py
```

You can then run a local gradio dashboard by running:

```sh
# terminal 1 to run the database server as a HttpClient: 
uv run chroma run --path ./data/.chromadb/rag_db

# terminal 2 to run the gradio dashboard : 
uv run gradio app.py
```

# Analysis tool guidelines

## Multi-lingual translation, geolocation and sentiment analysis

With Gemini 2.0 Flash:
```bash
uv run analysis.py https:t.me/<account_name>/<message_id>
```

With a baseline method (less efficient but does not require any GOOGLE_API_KEY):
```bash
uv run src/baselines/analysis.py https:t.me/<account_name>/<message_id>
```

## Similar message search

With Gemini 2.0 Flash:
```bash
uv run similar.py --post https:t.me/<account_name>/<message_id> --db ./.chroma
```

With a baseline method (less efficient but does not require any GOOGLE_API_KEY):
```bash
uv run src/baselines/similar.py --post https:t.me/<account_name>/<message_id> --db ./.chroma
```

## Retrieval-Augmented Generation (RAG)

With Gemini 2.0 Flash:
```bash
uv run rag.py --query "To be or not to be?" --db ./.chroma
```


