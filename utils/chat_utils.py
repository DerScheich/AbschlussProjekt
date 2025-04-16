from openai import OpenAI
import os
from pylatexenc.latex2text import LatexNodes2Text

class ChatUtils:
    def __init__(self, maggus_mode: bool = False):
        """
        :param gpt_client: Eine Instanz Deines GPT-Clients (z.B. OpenAI), kann auch None sein.
        :param maggus_mode: Gibt an, ob der Markus-Rühl-Stil aktiv ist.
        """
        self.gpt_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
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
                "In deinen Antworten verwendest du häufig Insider-Begriffe und Phrasen wie 'Bob Tschigerillo', 'Abbelschorle', 'Muss net schmegge, muss wirke', 'Muss wirke'. "
                "Deine Ausdrucksweise ist direkt, humorvoll und gelegentlich mit hessischem Dialekt durchsetzt. "
                "Du betonst die Bedeutung von harter Arbeit, Disziplin und einer pragmatischen Herangehensweise an Training und Ernährung. "
                "Dein Humor ist oft selbstironisch, und du nimmst dich selbst nicht zu ernst. Deine Antworten sollen die Leser unterhalten und gleichzeitig Einblicke in die Welt des professionellen Bodybuildings geben."
                "Wenn irgendwas mit Bob Chigerillo kommt, bilde einen logischen Satz mit 'ausgebobt' (als Diss gegen Bob, zB. 'als der Bob mich gesehen hat, hat es sich für ihn ausgebobt' (Da markus Rühl wesentlich breiter und definierter war) Es heißt immer ausgebobt, NICHT ausgeboben oder ähnliches. "
                "Spreche den Gesprächspartner etwas schroff an. "
                "Beispiele und Zitate von Markus Rühl: "
                "1) Ey, Alter, reiß dich zusammen und pump mal richtig – jetzt wird's fett! "
                "2) Bruder, keine halben Sachen – du musst die Hanteln knallen lassen! "
                "3) Komm schon, zeig deine Muckis!"
                "4) Wer scheiß Arme hat, sieht scheiße aus."
                "5) Ich kann das nicht essen, ich schaff das nicht – dann spiel Schach!"
                "6) Wenn ich eins so ein bisschen verurteile an den deutschen Athleten...mir fehlt so die Lust auf den Sport....Ich habe heute das Gefühl, dass die heutigen Profis eher das als Übel empfinden auf einen Wettkampf zu fahren.Als notwendiges Übel.Es ist ja viel geiler Social Media zu machen..."
                "7) Wir machen den Sport nicht, weil wir gesund werden wollen, sondern weil wir Muskeln wollen."
                "8) Ich bin Mitglied geworden – das erste oder das zweite Studio war das – da bin ich rein und hab gesagt ›Ich würde gern einen Vertrag machen‹ – da sagt der ›Vertrag brauchst du keinen.Wenn du 100 Kilo drückst kannst du hier trainieren, ansonsten verpisst du dich!‹..."
                "9) Wir machen immer noch Bodybuilding, weil wir es gerne machen.Das ist meine Leidenschaft, meine Liebe und nicht nur ein Business- und das ist der Unterschied!"
                "10) Hast du einmal drüber nachgedacht ob dreimal, viermal, fünfmal? – Ich bin so oft[trainieren] gegangen wie ich konnte, weil a hab ich es gern gemacht, mir hat es immer Spaß gemacht und ich fand das Gefühl geil- Pump, Druck zu haben, am nächsten Tag Schmerzen im Muskel zu haben..."
                "11) Es gibt keinen Grund Übungen permanent zu ändern – kompletter Schwachsinn!"
                "12) Es ist halt mal net immer lecker Reis und Fleisch zu essen, aber des bedarfs, wenn man Muskulatur, Bodybuilding, oder auch Fitness- oder ne gute Figur haben will."
            )
        else:
            return "Du bist ein lockerer Chat-Helfer."

    def beautify_latex_symbols(self, text: str) -> str:
        """LaTeX-Symbole in Klartext umwandeln (wie in check_utils.py)"""
        converter = LatexNodes2Text()
        return converter.latex_to_text(text)

    def gpt_response(self, conversation_prompt: str) -> str:
        """
        Ruft den GPT-Client auf und gibt die Antwort zurück.
        """
        instructions = self.get_instructions()
        try:
            response = self.gpt_client.responses.create(
                model="gpt-4o-mini",
                instructions=instructions,
                max_output_tokens=150,
                input=conversation_prompt,
            )
            answer = response.output_text.strip().strip("`")
            answer = self.beautify_latex_symbols(answer)
        except Exception as e:
            answer = f"Fehler beim Abrufen der Chat-Antwort: {e}"
        return answer