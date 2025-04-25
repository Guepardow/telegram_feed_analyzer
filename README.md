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

Main technology used: 
<a href="https://www.python.org/"><img src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/python.png" alt="Python" height="35px" style="vertical-align: middle;margin-left:15px;margin-right:25px"></a>
<a href="https://aistudio.google.com/app/apikey">
<img src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/gemini.png" alt="Gemini" height="35px" style="vertical-align: middle;margin-right:25px"></a>
<a href="https://docs.trychroma.com/docs/overview/introduction">
<img src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/chromadb.png" alt="ChromaDB" height="35px" style="vertical-align: middle;margin-right:25px"></a>
<a href="https://dash.plotly.com/">
<img src="https://mehdimiah.com/blog/telegram_feed_analyzer/icon/dash.png" alt="Dash" height="35px" style="vertical-align: middle;margin-right:25px"></a>

## Setup
This project uses `uv` as a project manager; you can [download it here](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/Guepardow/telegram_feed_analyzer
cd telegram_feed_analyzer
uv sync
```

## Authentification

You can get a [Google API key here (for free)](https://aistudio.google.com/app/apikey). Then, update the file `config.yaml` with this key.

[Optional] You can get a [Telethon API key here (for free)](https://docs.telethon.dev/en/stable/basic/signing-in.html). Then, update the file `config.yaml` with this key.

# Data

You can download 1987 "enhanced messages" posted on Telegram on March 31st, 2025 about the situation in Israel and Palestine:

```sh
wget -q https://mehdimiah.com/blog/telegram_feed_analyzer/data/data_telegram_250331.json -O ./data/telegram_250331.json
```

Check [data/README.md](data/README.md) for more information.

# Dash Dashboard

First, create Persistent Chroma databases for the embeddings (for the tasks on semantic search and retrieval). The databases will be stored in `./data/.chroma`):
```sh
cd src
uv run similarity_search.py  # build the Chroma database with the embeddings on semantic search
uv run rag.py  # build the Chroma database with the embeddings for the RAG system
```

You can then run a local Dash dashboard by running:

```sh
# terminal 1 to run the database server with the embeddings on semantic search as a HttpClient: 
uv run chroma run --path ./data/.chroma/similarity_search_db --host localhost --port 8000

# terminal 2 to run the database server with the embeddings on retrieval (RAG) as a HttpClient: 
uv run chroma run --path ./data/.chroma/rag_db --host localhost --port 8001

# terminal 3 to run the Dash dashboard: 
uv run app.py
```

# Analysis tool guidelines

## Multi-lingual translation, geolocation and sentiment analysis

With Gemini 2.0 Flash, run the analysis on a single post:
```bash
cd src ; uv run get_analysis.py --post https://t.me/<account_name>/<message_id> --method gemini
```

With a baseline method (less efficient but does not require any GOOGLE_API_KEY but requires CUDA):
```bash
cd src ; uv run get_analysis.py --post https://t.me/<account_name>/<message_id> --method baseline
```

## Similar message search

With Gemini 2.0 Flash:
```bash
cd src ; uv run similarity_search.py  # build the Chroma database with the embeddings
uv run chroma run --path ../data/.chroma/similarity_search_db --host localhost --port 8000  # terminal 1
uv run similarity_search.py --query "A huge explosion was heard in Rafah" # terminal 2
```

With a baseline method (less efficient but does not require any GOOGLE_API_KEY but requires CUDA):
```bash
cd src/baselines  ; uv run similarity_search.py  # build the Chroma database with the embeddings
uv run chroma run --path ../../data/.chroma/bert_db --host localhost --port 8000  # terminal 1
uv run similarity_search.py --query "A huge explosion was heard in Rafah" # terminal 2
```

## Retrieval-Augmented Generation (RAG)

With Gemini 2.0 Flash:
```bash
cd src ; uv run rag.py  # build the Chroma database with the embeddings
uv run chroma run --path ../data/.chroma/rag_db --host localhost --port 8001  # terminal 1
uv run rag.py --query "What happened in Rafah?"  # terminal 2
```


