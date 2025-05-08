from scipy.special import softmax
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

def load_model_sentiment():

    # Setup the sentiment analysis pipeline
    MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    model.eval()
    model= model.to(DEVICE)

    return tokenizer, model

def get_sentiment(text_english: str, tokenizer, model) -> dict[str, float]:
    """
    Get sentiment scores for the text using Hugging Face Transformers.
    Args:
        text_english (str): Text to be analyzed.
    """
    # Load the model and tokenizer
    
    text_tokenized = tokenizer(text_english[:500], return_tensors='pt')
    text_tokenized = text_tokenized.to(DEVICE)
    output = model(**text_tokenized)
    scores = output[0][0].detach().cpu().numpy()
    scores = softmax(scores)

    return {'negative': round(float(scores[0]), 3), 'neutral': round(float(scores[1]), 3), 'positive': round(float(scores[2]), 3)}

# tokenizer, model = load_model_sentiment()
# print(get_sentiment("I love programming!", tokenizer, model))
# print(get_sentiment("For the second time during weeks ... The occupation destroys two houses in Tuba Al -Zangaria, inside the occupied Palestinian, this morning", tokenizer, model))