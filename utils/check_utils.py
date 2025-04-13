import base64
import asyncio
from openai import OpenAI
from pylatexenc.latex2text import LatexNodes2Text  # Wir nutzen pylatexenc, da es keine separate "latex2text" Library gibt

def encode_image(image_bytes: bytes) -> str:
    """
    Codiert die Bilddaten als Base64-String im Data-URL-Format.
    Hier wird standardmäßig angenommen, dass es sich um ein PNG handelt.
    """
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:image/png;base64,{encoded}"

def beautify_latex_symbols(text: str) -> str:
    """
    Wandelt LaTeX-Ausdrücke in reinen Klartext um, sodass beispielsweise
    "\frac{U}{2 \pi}" als "U/2 π" erscheint.
    """
    converter = LatexNodes2Text()
    return converter.latex_to_text(text)

def process_response(response) -> str:
    """
    Extrahiert die Antwort aus dem GPT-Response-Objekt, bereinigt den Text
    und konvertiert eventuelle LaTeX-Ausdrücke in Klartext.
    """
    content = response.choices[0].message.content.strip().strip("`")
    content = beautify_latex_symbols(content)
    return content

def check_image(image_bytes: bytes, prompt: str) -> str:
    """
    Schickt das Bild und den Prompt an das GPT-Modell und gibt die Antwort zurück.

    :param image_bytes: Binärdaten des Bildes.
    :param prompt: Text, der angibt, was geprüft werden soll.
    :return: Die verarbeitete Antwort des GPT-Modells als Text.
    """
    base64_img = encode_image(image_bytes)
    client = OpenAI()

    # Nachrichteninhalt: Zuerst der Prompt als Text, danach das Bild als "image_url"
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": base64_img}}
            ]
        }
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Kostengünstiges, zuverlässiges Modell
            messages=messages,
            max_tokens=500,
        )
        return process_response(response)
    except Exception as e:
        return f"Fehler beim Abrufen der Antwort: {e}"

async def check_image_async(image_bytes: bytes, prompt: str) -> str:
    """
    Asynchroner Wrapper für check_image, um diesen in einem separaten Thread auszuführen.
    """
    return await asyncio.to_thread(check_image, image_bytes, prompt)
