from loguru import logger
import asyncio


async def translate_with_googletrans(text: str) -> str:
    """
    Translate text using Google Translate API.
    Args:
        text (str): Text to be translated.
    """
    from googletrans import Translator

    async with Translator() as translator:
        result = await translator.translate(text, dest='en')
        return (result.text)


def translate_with_transformers(text: str) -> str:
    """
    Translate text using Hugging Face Transformers.
    Args:
        text (str): Text to be translated.
    """
    import langid
    from transformers import pipeline

    # Detect the language of the text
    language = langid.classify(text)[0]

    # Translate the text to English if it's not already in English
    if language == 'en':
        text_english = text
    elif language == 'ar':
        translator_arabic = pipeline("translation", model="Helsinki-NLP/opus-mt-ar-en", device='cuda', ) 
        text_english = translator_arabic(text)[0]['translation_text']
    elif language == 'he':
        translator_hebrew = pipeline("translation", model="Helsinki-NLP/opus-mt-tc-big-he-en", device='cuda')
        text_english = translator_hebrew(text)[0]['translation_text']
    else:
        logger.warning(f"Language {language} not supported for translation. Skipping translation.")

    return text_english


text = '**للمرة الثانية خلال أسابيع... الاحتلال يهدم منزلين في طوبا الزنغرية بالداخل الفلسطيني المحتل، صباح اليوم**'

print(translate_with_transformers(text))
print(asyncio.run(translate_with_googletrans(text)))