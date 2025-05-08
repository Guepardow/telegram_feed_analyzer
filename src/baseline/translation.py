from googletrans import Translator


async def translate_with_googletrans(text: str) -> str:
    """
    Translate text using Google Translate API.
    Args:
        text (str): Text to be translated.
    """
    async with Translator() as translator:
        result = await translator.translate(text[:512], dest='en')
        return result.text

# text = '**للمرة الثانية خلال أسابيع... الاحتلال يهدم منزلين في طوبا الزنغرية بالداخل الفلسطيني المحتل، صباح اليوم**'
# print(asyncio.run(translate_with_googletrans(text)))