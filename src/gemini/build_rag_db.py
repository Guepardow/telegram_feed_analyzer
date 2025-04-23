import json
import yaml
from tqdm import tqdm

from google import genai
from google.genai import types

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings


class GeminiEmbeddingFunction(EmbeddingFunction):
    """
    Embed documents or query using Gemini
    """
    
    def __init__(self, genai_client, document_mode: bool = False):
        super().__init__()
        self.document_mode = document_mode
        self.genai_client = genai_client

    def __call__(self, input: Documents) -> Embeddings:

        embedding_task = "retrieval_document" if self.document_mode else "retrieval_query"

        response = self.genai_client.models.embed_content(
            model="models/embedding-001",
            contents=input,
            config=types.EmbedContentConfig(
                task_type=embedding_task,
            ),
        )
        return [e.values for e in response.embeddings]


def main():

    # Open JSON enhanced Telegram data
    with open('../../data/data_telegram_250331.json', 'r', encoding="utf-8") as f:
        data = json.load(f)

    # Format all Telegram message
    documents = [f"[Source: Telegram account {m['account']}] [Date: {m['date']}] {m['text_english_genai']}" for m in data]

    # Initialize the Google GenAI client
    GOOGLE_API_KEY = yaml.safe_load(open("../../config.yaml"))['secret_keys']['google']['api_key']
    genai_client = genai.Client(api_key=GOOGLE_API_KEY)
    
    # The embedding function is set a DOCUMENT mode: we will embed documents
    embed_fn = GeminiEmbeddingFunction(genai_client=genai_client, document_mode=True)

    # Initialize a persistent Chroma client
    chroma_client = chromadb.PersistentClient(path='../../data/.chromadb/rag_db')
    db = chroma_client.get_or_create_collection(name="telegram", embedding_function=embed_fn)

    # Add messages from Telegram 
    # NB: using batch is necessary since the maximal load is 100 samples and that our dataset contains 1987 documents
    for start in tqdm(range(0, len(documents), batch_size := 100)):
        end = min(start + batch_size, len(documents))
        db.add(documents=documents[start:end], ids=[str(i) for i in range(start, end)])


if __name__ == '__main__':
    main()
# uv run build_rag_db.py