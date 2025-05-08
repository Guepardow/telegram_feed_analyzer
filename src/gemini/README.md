# Gemini

This folder contains the Gemini approach to solve the following tasks using generative AI:
- translation;
- geolocation;
- sentiment analysis;

# Analyze on a single post

To analyze a single post, run:
```sh
uv run analyze_post.py --post https://t.me/<account_name>/<message_id>
```

# Find similar post in a datamap

To find the most similar post to a specific query, run:

```sh
uv run similarity_search.py  --datamap <datamap>  # build the Chroma database with the embeddings001 embeddings
uv run chroma run --path ../../data/<datamap>/.chroma/bert_db --host localhost --port 8000  # terminal 1
uv run similarity_search.py --query <query> # terminal 2
```

# Ask a question using the RAG system

To ask a question to a datamap, run:

```sh
uv run rag.py --datamap <datamap>  # build the Chroma database with the embeddings001 embeddings
uv run chroma run --path ../../data/<datamap>/.chroma/rag_db --host localhost --port 8001  # terminal 1
uv run rag.py --query <query> # terminal 2
```