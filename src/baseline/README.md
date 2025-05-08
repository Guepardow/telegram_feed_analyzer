# Baseline

This folder contains the baseline approach to solve the following tasks:
- translation: we use googletrans to translate to English;
- geolocation: we use Named Entity Recognition on the translated text to find the name of locations and geopy to geolocate them;
- sentiment analysis: we use the library transformers to compute the negativity, neutrality and positivity scores.

# Analyze on a single post

To analyze a single post, run:
```sh
uv run analyze_post.py --post https://t.me/<account_name>/<message_id>
```

# Find similar post in a datamap

To find the most similar post to a specific query, run:

```sh
uv run similarity_search.py  --datamap <datamap>  # build the Chroma database with the BERT embeddings
uv run chroma run --path ../../data/datamaps/<datamap>/.chroma/bert_db --host localhost --port 8000  # terminal 1
uv run similarity_search.py --query <query> # terminal 2
```

# Ask a question using the RAG system

No available with the baseline approach. Please see [gemini/README.md](../gemini/README.md).