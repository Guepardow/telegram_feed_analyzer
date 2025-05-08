import os
import json
import yaml
import click
from tqdm import tqdm
from loguru import logger

from google import genai
from google.genai import types

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings


class GeminiEmbeddingSemanticSimilarity(EmbeddingFunction):
    """
    Embed documents for semantic similarity using Gemini
    """
    def __init__(self, genai_client):
        super().__init__()
        self.genai_client = genai_client

    def __call__(self, input: Documents) -> Embeddings:

        response = self.genai_client.models.embed_content(
            model="models/embedding-001",
            contents=input,
            config=types.EmbedContentConfig(task_type='semantic_similarity')
            )

        return [e.values for e in response.embeddings]


class SimilaritySearch:

    def __init__(self, GOOGLE_API_KEY: str):

        # Initialize the GenAI client
        self.genai_client = genai.Client(api_key=GOOGLE_API_KEY)
        self.embedding_function = GeminiEmbeddingSemanticSimilarity(genai_client=self.genai_client)

    def create_collection(self, persist_directory):

        # Initialize a persistent Chroma client
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.chroma_client.create_collection(
            name='similarity_search_db',
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )    

    def load_collection(self, host='localhost', port=8000):
        # Initialize a Chroma client
        self.chroma_client = chromadb.HttpClient(host=host, port=port)
        self.collection = self.chroma_client.get_collection(
            name="similarity_search_db", 
            embedding_function=self.embedding_function
            )
        
    def add_documents(self, documents):

        # Add documents using batches
        # NB: using batch is necessary since the maximal load is 100 samples and that our dataset contains 1987 documents
        for start in tqdm(range(0, len(documents), batch_size := 100)):
            end = min(start + batch_size, len(documents))
            self.collection.add(documents=documents[start:end], ids=[str(i) for i in range(start, end)])

    def query(self, query: str, n_results: int = 5):

        # Return the n_results most similar documents to the query
        query_embeddings = self.embedding_function([query])
        return self.collection.query(query_embeddings, n_results=n_results)
        

def build_database(datamap: str):
    
    # Get the API key from the config file
    with open('../../config.yaml') as f:
        config = yaml.safe_load(f)
        GOOGLE_API_KEY = config['secret_keys']['google']['api_key']

    # Initialize the SimilaritySearch class
    similarity_search = SimilaritySearch(GOOGLE_API_KEY=GOOGLE_API_KEY)
    similarity_search.create_collection(persist_directory=os.path.join('../../data/datamaps', datamap, '.chroma/similarity_search_db'))

    # Load the documents from the JSON file
    with open(os.path.join('../../data/datamaps', datamap, 'telegram_gemini.json'), 'r', encoding="utf-8") as f:
        data = json.load(f)

    documents = [f"[Date: {m['date']}] {m['text_english']}" for m in data]
    logger.info(f"Number of documents: {len(documents)}")

    # Add documents to the collection
    similarity_search.add_documents(documents=documents)


def search(query: str, n_results: int):
    
    # Get the API key from the config file
    with open("../../config.yaml") as f:
        config = yaml.safe_load(f)
        GOOGLE_API_KEY = config['secret_keys']['google']['api_key']

    # Initialize the SimilaritySearch class
    similarity_search = SimilaritySearch(GOOGLE_API_KEY=GOOGLE_API_KEY)
    similarity_search.load_collection(host="localhost", port=8000)

    # Search for similar documents
    results = similarity_search.query(query, n_results=n_results)
    return results


@click.command()
@click.option('--datamap', required=False, help="Name of the datamap")
@click.option('--query', required=False, help='Query to search for similar message')
def main(datamap=None, query=None):
    
        # Build mode
        if (query is None) and (datamap is not None):
            build_database(datamap)
    
        # Query mode
        else:
            results = search(query=query, n_results=5)
            for dist, doc in zip(results['distances'][0], results['documents'][0]):
                print(f"Distance: {dist:0.3f}\t{doc}")


if __name__ == "__main__":
    main()

# uv run similarity_search.py --datamap sample                                                                     # build database on terminal 1
# uv run chroma run --path ../../data/datamaps/sample/.chroma/similarity_search_db --host localhost --port 8000    # host the database on terminal 1
# uv run similarity_search.py --query "A huge explosion was heard in Rafah"                                        # query the database on terminal 2

# Expected output:
# Distance: 0.128 [Date: 2025-03-31 23:52:43] The latest explosion in the city of Rafah was heard throughout the Gaza Strip.
# Distance: 0.133 [Date: 2025-03-31 19:33:56] Again, violent explosions north of the city of Rafah.
# Distance: 0.140 [Date: 2025-03-31 19:36:55] Strong explosions are heard between the city of Khan Yunis and Rafah
# Distance: 0.151 [Date: 2025-03-31 02:20:07] Urgent: New explosion in the Tel Sultan neighborhood of Rafah
# Distance: 0.153 [Date: 2025-03-31 02:24:42] Blowing up a residential square in Al-Sultan neighborhood, west of Rafah, and the sound of its explosion was heard from the central governorate.