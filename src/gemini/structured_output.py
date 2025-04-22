from google import genai
from google.genai import types
# from google.api_core import retry
# from IPython.display import Markdown, display
import yaml
import typing_extensions as typing


GOOGLE_API_KEY = yaml.safe_load(open("../../config.yaml"))['secret_keys']['google']['api_key']
client = genai.Client(api_key=GOOGLE_API_KEY)

# is_retriable = lambda e: (isinstance(e, genai.errors.APIError) and e.code in {429, 503})
# if not hasattr(genai.models.Models.generate_content, '__wrapped__'):
#   genai.models.Models.generate_content = retry.Retry(
#       predicate=is_retriable)(genai.models.Models.generate_content)


COMBINED_PROMPT = """
You are a multifunctional assistant capable of translating, geolocating, and analyzing sentiment from a given Telegram post.
These messages on posted on channels based in the Middle East (mainly, Gaza, Israel and West Bank).

Telegram Message:
```
{text}
```

Tasks:

1. Translation:
    a. Identify the language of the post. It could be in Arabic, Hebrew, or English.
    b. Translate the post to English accurately.
    c. Maintain the original formatting, including paragraph breaks, lists, and emphasis.
    d. Ensure cultural references, idioms, and slang are appropriately translated or explained.
    e. Preserve the tone of the post, whether it is formal, informal, or conversational.
    f. Return only the translated post and not the language

2. Geolocation:
    a. Read carefully to find any current factual events. Ignore speeches and announcements. Ignore very old events and future events.
    b. Read the post carefully to identify any mentioned locations, such as cities, landmarks, or addresses.
    c. Find the location (most precise if many) of the factual event based on the context provided.
    d. Provide the latitude and longitude of the identified location in decimal degrees format.
    e. Return only the location and their coordinates in the format [(location_name: str, latitude: float, longitude: float)]

Examples:

Example 1:
Telegram Post:
```
A protest took place in front of the Al-Aqsa Mosque today, with hundreds of participants.
```
Output for geolocation task:
[("Al-Aqsa Mosque", 31.776, 35.235)]
Explanation: The event is a protest, which is a factual event that can be recorded on video.

Example 2:
Telegram Post:
```
The Prime Minister will deliver a speech tomorrow at the Knesset.

```
Output for geolocation task:
[]
Explanation: The event is a future speech, which is not a factual event that has already occurred.

Example 3:
Telegram Post:
```
There are power outages in Rafah, in the southern Gaza Strip.
```
Output for geolocation task:
[("Rafah", 31.294, 34.248)]
Explanation: Only the most precise location is reported.

Example 4:
Telegram Post:
```
The President visited Jerusalem where he discussed the events that took place in Jenin last week.
```
Output for geolocation task:
[("Jerusalem", 31.777, 35.232)]
Explanation: Only the events that recently happened are geolocated.

3. Sentiment Analysis:
    a. Read the message carefully to understand its content and tone.
    b. Evaluate the sentiment of the message.
    c. Return only the three probabilities as a tuple without any explanation
    d. Ensure the probabilities sum up to 1.0.

Output:
- translation: str
- geolocation: [(location_name: str, latitude: float, longitude: float)]
- sentiment: (negative: float, neutral: float, positive: float)
"""


class Geoloc(typing.TypedDict):
  location_name: str
  latitude: float
  longitude: float

class Sentiment(typing.TypedDict):
  negative: float
  neutral: float
  positive: float
    
class StructuredAnalysis(typing.TypedDict):
  translation: str
  geolocations: list[Geoloc]
  sentiment: Sentiment


def structured_analysis(text: str, prompt_template: str):

  structured_output_config = types.GenerateContentConfig(
      temperature=0.1,
      response_mime_type="application/json",
      response_schema=StructuredAnalysis,
  )
  response = client.models.generate_content(
      model='gemini-2.0-flash',
      config=structured_output_config,
      contents=[prompt_template.format(text=text)],
  )

  return response.parsed


text = '**للمرة الثانية خلال أسابيع... الاحتلال يهدم منزلين في طوبا الزنغرية بالداخل الفلسطيني المحتل، صباح اليوم**'
print(structured_analysis(text, COMBINED_PROMPT))