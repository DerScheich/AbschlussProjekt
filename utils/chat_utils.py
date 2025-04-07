from openai import OpenAI
import os

client = OpenAI(
    api_key = os.getenv("OPENAI_API_KEY"),
)

class ChatUtils:
    def __init__(self, gpt_client=None, maggus_mode: bool = False):
        """
        :param gpt_client: Eine Instanz Deines GPT-Clients (z.B. OpenAI), kann auch None sein.
        :param maggus_mode: Gibt an, ob der Markus-Rühl-Stil aktiv ist.
        """
        self.gpt_client = gpt_client
        self.maggus_mode = maggus_mode

    def ape_transform(self, text: str) -> str:
        """Transformiert einen Text in abwechselnde Groß-/Kleinschreibung."""
        new_text = ""
        use_upper = False
        for char in text:
            if char.isalpha():
                new_text += char.upper() if use_upper else char.lower()
                use_upper = not use_upper
            else:
                new_text += char
        return new_text

    def get_instructions(self) -> str:
        """Gibt die Anweisungen für den GPT-Client basierend auf dem maggus_mode zurück."""
        if self.maggus_mode:
            return (
                "Du bist Markus Rühl, ein renommierter deutscher Profi-Bodybuilder, "
                "bekannt für deine beeindruckende Muskelmasse und deinen unverwechselbaren Humor. "
                "In deinen Antworten verwendest du häufig Insider-Begriffe und Phrasen wie 'Bob Tschigerillo', 'Abbelschorle', 'Muss net schmegge, muss wirke', 'Muss wirke' und 'Leck meine Eier'. "
                "Deine Ausdrucksweise ist direkt, humorvoll und gelegentlich mit hessischem Dialekt durchsetzt. "
                "Du betonst die Bedeutung von harter Arbeit, Disziplin und einer pragmatischen Herangehensweise an Training und Ernährung. "
                "Dein Humor ist oft selbstironisch, und du nimmst dich selbst nicht zu ernst. Deine Antworten sollen die Leser unterhalten und gleichzeitig Einblicke in die Welt des professionellen Bodybuildings geben."
                "Wenn irgendwas mit Bob Chigerillo kommt, bilde einen logischen Satz mit 'ausgebobt' (als Diss gegen Bob, zB. 'als der Bob mich gesehen hat, hat es sich für ihn ausgebobt' (Da markus Rühl wesentlich breiter und definierter war). "
                "Spreche den Gesprächspartner etwas schroff an. "
                "Beispiele: "
                "1) Ey, Alter, reiß dich zusammen und pump mal richtig – jetzt wird's fett! "
                "2) Bruder, keine halben Sachen – du musst die Hanteln knallen lassen! "
                "3) Komm schon, zeig deine Muckis!"
            )
        else:
            return "Du bist ein lockerer Chat-Helfer. Antworte kurz."

    def gpt_response(self, conversation_prompt: str) -> str:
        """
        Ruft den GPT-Client auf und gibt die Antwort zurück.
        """
        instructions = self.get_instructions()
        try:
            response = client.responses.create(
                model="gpt-4o-mini",
                instructions=instructions,
                max_output_tokens=150,
                input=conversation_prompt,
            )
            answer = response.output_text.strip()
        except Exception as e:
            answer = f"Fehler beim Abrufen der Chat-Antwort: {e}"
        return answer