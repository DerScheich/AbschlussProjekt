import base64
import asyncio
from openai import OpenAI
from pylatexenc.latex2text import LatexNodes2Text

"""
Hilfsfunktionen für Bildprüfung via GPT: Encoding, API-Call, Response-Processing.
"""

def encode_image(image_bytes: bytes) -> str:
    """
    Encodiert Bild-Bytes als Base64 Data-URL.

    :param image_bytes: Binäre Bilddaten.
    :return: Data-URL-String.
    """
    # Base64-Codierung
    encoded = base64.b64encode(image_bytes).decode()
    return f"data:image/png;base64,{encoded}"


def beautify_latex_symbols(text: str) -> str:
    """
    Wandelt LaTeX-Ausdrücke in Klartext um.

    :param text: Text mit LaTeX.
    :return: Bereinigter Text.
    """
    # LaTeX zu Text
    converter = LatexNodes2Text()
    return converter.latex_to_text(text)


def process_response(response) -> str:
    """
    Extrahiert und bereinigt GPT-Antwort.

    :param response: GPT-Response-Objekt.
    :return: Fertiger Antworttext.
    """
    # Inhalt holen
    content = response.choices[0].message.content.strip().strip('`')
    return beautify_latex_symbols(content)


def check_image(image_bytes: bytes, prompt: str) -> str:
    """
    Ruft GPT auf, um Bild basierend auf Prompt zu prüfen.

    :param image_bytes: Bilddaten als Bytes.
    :param prompt: Prüf-Prompt.
    :return: GPT-Ergebnis als Text.
    """
    # Bild encodieren
    base64_img = encode_image(image_bytes)
    client = OpenAI()
    # Nachrichten für GPT
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": base64_img}}
        ]
    }]
    try:
        # API-Call
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500
        )
        return process_response(response)
    except Exception as e:
        return f"Fehler beim Abruf: {e}"


async def check_image_async(image_bytes: bytes, prompt: str) -> str:
    """
    Asynchroner Wrapper für check_image via Thread.

    :param image_bytes: Bilddaten.
    :param prompt: Prüf-Prompt.
    :return: GPT-Ergebnis als Text.
    """
    # in Thread auslagern
    return await asyncio.to_thread(check_image, image_bytes, prompt)