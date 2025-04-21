# Telegram Feed Analyzer

<p align="center">
    <img src="https://www.mehdimiah.com/blog/telegram_feed_analyzer/main_400p.png" alt="Headline image" width="600"/><br>
    Illustration of some cases where journalists face difficulties accessing the field: war,  natural disasters or military restrictions.
</p>

This project enhances Telegram feeds, using the Gemini AI API, by adding the following capabilities:
- 🗺️ translation to English;
- 📍 geolocation;
- 😳 sentiment analysis;
- ✉️ similar message search;
- ❓ retrieval-augmented generation

# Installation

This project uses `uv` as a project manager; you can [download it here](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/Guepardow/telegram_feed_analyzer
cd telegram_feed_analyzer
uv sync
```

# Gradio Dashboard

You can run a local gradio dashboard by running:

```sh
uv run gradio app.py
```





