import yaml
import json
import click
from tqdm import tqdm
from loguru import logger

from google import genai
from google.genai import types

import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings


class GeminiEmbeddingFunction(EmbeddingFunction):
    """
    Embed documents or query using Gemini
    """
    
    def __init__(self, genai_client, task_type="retrieval_query"):
        super().__init__()
        self.task_type = task_type
        self.genai_client = genai_client

    def __call__(self, input: Documents) -> Embeddings:

        response = self.genai_client.models.embed_content(
            model="models/embedding-001",
            contents=input,
            config=types.EmbedContentConfig(
                task_type=self.task_type,
            ),
        )
        return [e.values for e in response.embeddings]


class RAG:

    def __init__(self, GOOGLE_API_KEY: str):

        # Initialize the GenAI client
        self.genai_client = genai.Client(api_key=GOOGLE_API_KEY)

        # Embedding functions
        self.embedding_function_docus = GeminiEmbeddingFunction(genai_client=self.genai_client, task_type="retrieval_document")
        self.embedding_function_query = GeminiEmbeddingFunction(genai_client=self.genai_client, task_type="retrieval_query")

    def create_collection(self, persist_directory):
        # Initialize a persistent Chroma client using the embedding function for documents
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.chroma_client.create_collection(
            name='rag',
            embedding_function=self.embedding_function_docus,
            metadata={"hnsw:space": "cosine"}
        )

    def load_collection(self, host, port):
        # Initialize a Chroma client using the embedding function for queries
        self.chroma_client = chromadb.HttpClient(host=host, port=port)
        self.collection = self.chroma_client.get_collection(
            name="rag", 
            embedding_function=self.embedding_function_query)

    def add_documents(self, documents):

        # Add documents using batches
        # NB: using batch is necessary since the maximal load is 100 samples and that our dataset contains 1987 documents
        for start in tqdm(range(0, len(documents), batch_size := 100)):
            end = min(start + batch_size, len(documents))
            self.collection.add(documents=documents[start:end], ids=[str(i) for i in range(start, end)])

    def query(self, query, n_results):
        result = self.collection.query(query_texts=query, n_results=n_results)

        [all_passages] = result["documents"]
        query_oneline = query.replace("\n", " ")
        prompt = f"""
        You are a knowledgeable and professional journalism bot specializing in fact-checking and international humanitarian law.
        You answer questions using text from the reference passage included below. Be sure to respond in complete sentences, providing comprehensive and well-researched information.
        Adopt a journalistic tone.

        Since the data come from Telegram, be cautious, as it is from a social network and the information can be inaccurate.
        Each passage corresponds to a Telegram post: the content, the account and the date of the post are mentioned in each passage.
        Keep in mind that several hours may pass between an event and the publication of a message related to it.

        If the passage is irrelevant to the answer, you may ignore it.

        QUESTION: {query_oneline}
        """
        for passage in all_passages:
            passage_oneline = passage.replace("\n", " ")
            prompt += f"PASSAGE: {passage_oneline}\n"

        answer = self.genai_client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.1)
        )
        return answer.text


def build_database():

    # Get the API key from the config file
    with open("../config.yaml") as f:
        config = yaml.safe_load(f)
        GOOGLE_API_KEY = config['secret_keys']['google']['api_key']

    # Initialize the RAG system
    rag = RAG(GOOGLE_API_KEY=GOOGLE_API_KEY)
    rag.create_collection(persist_directory="../data/.chroma/rag_db")

    # Load the documents from the JSON file
    with open('../data/data_telegram_250331.json', 'r', encoding="utf-8") as f:
        data = json.load(f)

    documents = [f"[Source: Telegram account {m['account']}] [Date: {m['date']}] {m['text_english_genai']}" for m in data]
    logger.info(f"Number of documents: {len(documents)}")

    # Add documents to the collection
    rag.add_documents(documents=documents)

def answer(query: str, n_results: int):

    with open("../config.yaml") as f:
        config = yaml.safe_load(f)
        GOOGLE_API_KEY = config['secret_keys']['google']['api_key']

    # Initialize the RAG system
    rag = RAG(GOOGLE_API_KEY=GOOGLE_API_KEY)
    rag.load_collection(host='localhost', port=8000)

    # Query the system
    answer = rag.query(query=query, n_results=n_results)
    return answer
    

@click.command()
@click.option('--query', required=False, help='Question to ask to the RAG system')
def main(query=None):

    # Build mode
    if query is None:
        build_database()

    # Query mode
    else:
        generated_answer = answer(query=query, n_results=20)
        print(generated_answer)


if __name__ == "__main__":
    main()

# build database: uv run rag.py
# host the database: uv run chroma run --path ../data/.chroma/rag_db --host localhost --port 8001

# query the database: uv run rag.py --query "What happened in Rafah?"