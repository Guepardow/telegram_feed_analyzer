import langid
from loguru import logger
from transformers import pipeline
from googletrans import Translator


async def translate_with_googletrans(text: str) -> str:
    """
    Translate text using Google Translate API.
    Args:
        text (str): Text to be translated.
    """
    async with Translator() as translator:
        result = await translator.translate(text, dest='en')
        return (result.text)


def load_model_translation():
    translator_arabic = pipeline("translation", model="Helsinki-NLP/opus-mt-ar-en", device='cuda') 
    translator_hebrew = pipeline("translation", model="Helsinki-NLP/opus-mt-tc-big-he-en", device='cuda')

    return translator_arabic, translator_hebrew


def translate_with_transformers(text: str, translator_arabic, translator_hebrew) -> str:
    """
    Translate text using Hugging Face Transformers.
    Args:
        text (str): Text to be translated.
    """

    # Detect the language of the text
    language = langid.classify(text)[0]

    # Translate the text to English if it's not already in English
    if language == 'en':
        text_english = text
    elif language == 'ar':
        text_english = translator_arabic(text)[0]['translation_text']
    elif language == 'he':
        text_english = translator_hebrew(text)[0]['translation_text']
    else:
        logger.warning(f"Language {language} not supported for translation. Skipping translation.")

    return text_english


# text = '**للمرة الثانية خلال أسابيع... الاحتلال يهدم منزلين في طوبا الزنغرية بالداخل الفلسطيني المحتل، صباح اليوم**'

# translator_arabic, translator_hebrew = load_model_translation()
# print(translate_with_transformers(text, translator_arabic, translator_hebrew))
# print(asyncio.run(translate_with_googletrans(text)))