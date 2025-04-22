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
    <a href="https://www.kaggle.com/code/guepardow/telegram-feed-analyzer">Blog post</a>
</p>

This project enhances Telegram feeds, using the Gemini AI API, by adding the following capabilities:
- 🗺️ translation to English;
- 📍 geolocation;
- 😳 sentiment analysis;
- ✉️ similar message search;
- ❓ retrieval-augmented generation (RAG)

# Installation

This project uses `uv` as a project manager; you can [download it here](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/Guepardow/telegram_feed_analyzer
cd telegram_feed_analyzer
uv sync
```

You can ket a GOOGLE API KEY [here](https://aistudio.google.com/app/apikey).

# Gradio Dashboard

You can run a local gradio dashboard by running:

```sh
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
uv run similar.py --post https:t.me/<account_name>/<message_id> --database data/telegram.json
```

With a baseline method (less efficient but does not require any GOOGLE_API_KEY):
```bash
uv run src/baselines/similar.py --post https:t.me/<account_name>/<message_id> --database data/telegram.json
```

## Retrieval-Augmented Generation (RAG)

With Gemini 2.0 Flash:
```bash
uv run rag.py --query "To be or not to be?" --database data/telegram.json
```


