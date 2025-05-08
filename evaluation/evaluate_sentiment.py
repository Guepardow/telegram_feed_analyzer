import json
import yaml
import enum
import click
from tqdm import tqdm
from google import genai
from google.genai import types
from google.api_core import retry
from collections import Counter


class AnswerComparison(enum.Enum):
  A = 'A'
  SAME = 'SAME'
  B = 'B'


def is_retriable(e):
    return isinstance(e, genai.errors.APIError) and e.code in {429, 503}

if not hasattr(genai.models.Models.generate_content, '__wrapped__'):
  genai.models.Models.generate_content = retry.Retry(
      predicate=is_retriable)(genai.models.Models.generate_content)



SENTIMENT_EVALUATION_PROMPT = """\
# Instruction
You are an expert evaluator. Your task is to evaluate the performance of two sentiment analysis models on posts from Telegram. 
You will be provided with a Telegram post and the sentiment predictions from two models. Your goal is to assess the accuracy and appropriateness of these predictions based on the provided criteria.

# Evaluation
## Metric Definition
You will be assessing sentiment analysis quality, which measures how well each model predicts the sentiment of a given Telegram post. Sentiment can be positive, negative, or neutral. 
Pay special attention to the nuances in language that might affect sentiment, such as sarcasm, irony, or subtle emotional cues.

## Criteria
Accuracy: The prediction accurately reflects the sentiment conveyed in the post.
Contextual Understanding: The model understands the context in which words are used, including idioms, cultural references, and figurative language.
Consistency: The model's predictions are consistent across similar posts with similar sentiments.
Granularity: The model can differentiate between subtle differences in sentiment, such as mild positivity versus strong enthusiasm.

## Rating Rubric
- "A": Model A's prediction is more accurate and appropriate than Model B's.
- "SAME": Both models' predictions are equally accurate and appropriate.
- "B": Model B's prediction is more accurate and appropriate than Model A's.

## Evaluation Steps
STEP 1: Read the Telegram post carefully to understand its sentiment.
STEP 2: Compare the sentiment predictions from Model A and Model B with your understanding of the post's sentiment.
STEP 3: Rate the predictions using the Rating Rubric.
STEP 4: Provide a brief explanation for your rating, highlighting any specific aspects of the post that influenced your decision.

# Telegram Post and Model Predictions
## Telegram Post
{text}

## Model Predictions
### Model A (negative score, neutral score, positivie score)
Sentiment: {model_a_neg}, {model_a_neu}, {model_a_pos}

### Model B (negative score, neutral score, positivie score)
Sentiment: {model_b_neg}, {model_b_neu}, {model_b_pos}
"""

def eval_pairwise_sentiment(client, text, model_a_neg, model_a_neu, model_a_pos, model_b_neg, model_b_neu, model_b_pos):
  """Determine the better of two answers to the same prompt."""

  chat = client.chats.create(model='gemini-2.5-flash-preview-04-17')

  # Generate the full text response.
  response = chat.send_message(
      message=SENTIMENT_EVALUATION_PROMPT.format(
          text=[text],
          model_a_neg=model_a_neg, model_a_neu=model_a_neu, model_a_pos=model_a_pos,
          model_b_neg=model_b_neg, model_b_neu=model_b_neu, model_b_pos=model_b_pos)
  )
  verbose_eval = response.text

  # Coerce into the desired structure.
  structured_output_config = types.GenerateContentConfig(
      response_mime_type="application/json",
      response_schema=AnswerComparison,
  )
  response = chat.send_message(
      message="Convert the final score.",
      config=structured_output_config,
  )
  structured_eval = response.parsed

  return verbose_eval, structured_eval


@click.command()
@click.option('--method_a', required=True, type=str, help="Name of the first Gemini model")
@click.option('--method_b', required=True, type=str, help="Name of the second Gemini model")
def main(method_a, method_b):

    # Open data
    with open(f"./results/{method_a}.json", encoding='utf-8') as file:
        messages_A = json.load(file)

    with open(f"./results/{method_b}.json", encoding='utf-8') as file:
        messages_B = json.load(file)

    # Login to the Google API
    with open('../config.yaml') as f:
        config = yaml.safe_load(f)
        GOOGLE_API_KEY = config['secret_keys']['google']['api_key']

    client = genai.Client(api_key=GOOGLE_API_KEY)

    # Vote between the two outputs
    votes = []
    for message_A, message_B in tqdm(zip(messages_A, messages_B), total=len(messages_A)):

        model_a_neg, model_a_neu, model_a_pos = message_A['negative'], message_A['neutral'], message_A['positive']
        model_b_neg, model_b_neu, model_b_pos = message_B['negative'], message_B['neutral'], message_B['positive']
        
        text_eval, struct_eval = eval_pairwise_sentiment(
            client=client,
            text=message_A['text'],
            model_a_neg=model_a_neg, model_a_neu=model_a_neu, model_a_pos=model_a_pos,
            model_b_neg=model_b_neg, model_b_neu=model_b_neu, model_b_pos=model_b_pos
        )
        
        if struct_eval:
            votes.append(struct_eval.value)

    print(Counter(votes))


if __name__ == '__main__':
    main()
