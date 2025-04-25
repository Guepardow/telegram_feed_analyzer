import json
import click
from tqdm import tqdm
from loguru import logger
import torch
from transformers import BertModel, BertTokenizer


import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings


class BERTEmbeddings(EmbeddingFunction):
    """
    Embed documents for semantic similarity using BERT
    """

    def __init__(self, model_name='bert-base-cased'):
        super().__init__()
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        self.model_name = model_name
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.model = BertModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

    def __call__(self, inputs: Documents) -> Embeddings:

        inputs = self.tokenizer(inputs, return_tensors='pt', padding=True, truncation=True)

        inputs=inputs.to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)
        embeddings = outputs.last_hidden_state[:, 0, :].squeeze().detach().cpu().numpy()  # CLS token
        return embeddings


class SimilaritySearch:

    def __init__(self):

        # Initialize the GenAI client
        self.embedding_function = BERTEmbeddings()

    def create_collection(self, persist_directory):

        # Initialize a persistent Chroma client
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.chroma_client.create_collection(
            name='bert_db',
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )    

    def load_collection(self, host, port):
        # Initialize a Chroma client
        self.chroma_client = chromadb.HttpClient(host=host, port=port)
        self.collection = self.chroma_client.get_collection(
            name="bert_db", 
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
        

def build_database():

    # Initialize the SimilaritySearch class
    similarity_search = SimilaritySearch()
    similarity_search.create_collection(persist_directory="../../data/.chroma/bert_db")

    # Load the documents from the JSON file
    with open('../../data/data_telegram_250331.json', 'r', encoding="utf-8") as f:
        data = json.load(f)

    documents = [f"[Date: {m['date']}] {m['text_english_genai']}" for m in data]
    logger.info(f"Number of documents: {len(documents)}")

    # Add documents to the collection
    similarity_search.add_documents(documents=documents)


def search(query: str, n_results: int):

    # Initialize the SimilaritySearch class
    similarity_search = SimilaritySearch()
    similarity_search.load_collection(host="localhost", port=8000)

    # Search for similar documents
    results = similarity_search.query(query, n_results=n_results)
    return results


@click.command()
@click.option('--query', required=False, help='Query to search for similar message')
def main(query=None):
    
        # Build mode
        if query is None:
            build_database()
    
        # Query mode
        else:
            results = search(query=query, n_results=5)
            for dist, doc in zip(results['distances'][0], results['documents'][0]):
                print(f"Distance: {dist:0.3f}\t{doc}")


if __name__ == "__main__":
    main()

# build database: uv run similarity_search.py
# host the database: uv run chroma run --path ../../data/.chroma/bert_db --host localhost --port 8000

# query the database: uv run similarity_search.py --query "A huge explosion was heard in Rafah"