import json
from datetime import datetime, date
import os

BIRTHDAY_FILE = "birthdays.json"

class BirthdayUtils:
    """
    Diese Klasse verwaltet die Geburtstage pro Guild.
    Die Daten werden als verschachteltes Dictionary gespeichert und in einer JSON-Datei persistiert.
    Struktur:
      {
         "guild_id1": {
             "user_id1": {"birthday": "YYYY-MM-DD", "last_wished": "2023" oder None},
             "user_id2": { ... }
         },
         "guild_id2": { ... }
      }
    """
    def __init__(self):
        self.birthdays = {}  # guild_id -> { user_id: {birthday, last_wished} }
        self.load_birthdays()

    def load_birthdays(self):
        if os.path.exists(BIRTHDAY_FILE):
            try:
                with open(BIRTHDAY_FILE, "r") as f:
                    self.birthdays = json.load(f)
            except Exception as e:
                print(f"Error loading birthdays: {e}")

    def save_birthdays(self):
        try:
            with open(BIRTHDAY_FILE, "w") as f:
                json.dump(self.birthdays, f, indent=4)
        except Exception as e:
            print(f"Error saving birthdays: {e}")

    def set_birthday(self, guild_id: str, user_id: str, birthday_str: str) -> str:
        """
        Versucht, den Geburtstag (im Format TT.MM.JJJJ) für den User zu speichern.
        Falls bereits ein Geburtstag gesetzt wurde, wird eine entsprechende Meldung zurückgegeben.
        """
        try:
            birthday = datetime.strptime(birthday_str, "%d.%m.%Y").date()
        except ValueError:
            return "Ungültiges Datumsformat. Bitte verwende TT.MM.JJJJ."

        if guild_id not in self.birthdays:
            self.birthdays[guild_id] = {}

        if user_id in self.birthdays[guild_id]:
            return "Du hast bereits deinen Geburtstag gesetzt."

        self.birthdays[guild_id][user_id] = {
            "birthday": birthday.strftime("%Y-%m-%d"),
            "last_wished": None
        }
        self.save_birthdays()
        return f"Dein Geburtstag wurde auf {birthday.strftime('%d.%m.%Y')} gesetzt."

    def check_birthdays(self, guild_id: str):
        """
        Prüft für eine bestimmte Guild, welche User heute Geburtstag haben und
        ob noch nicht in diesem Jahr gewünscht wurde.
        Gibt eine Liste mit Tupeln (user_id, birthday) zurück.
        """
        today = date.today()
        birthday_users = []
        if guild_id not in self.birthdays:
            return birthday_users

        for user_id, info in self.birthdays[guild_id].items():
            try:
                bday = datetime.strptime(info["birthday"], "%Y-%m-%d").date()
                last_wished = info.get("last_wished")
                if bday.month == today.month and bday.day == today.day:
                    if last_wished is None or int(last_wished) < today.year:
                        birthday_users.append((user_id, bday))
                        self.birthdays[guild_id][user_id]["last_wished"] = str(today.year)
            except Exception as e:
                print(f"Error processing birthday for user {user_id} in guild {guild_id}: {e}")
        if birthday_users:
            self.save_birthdays()
        return birthday_users

    def get_age(self, birthday_date: date) -> int:
        """
        Berechnet das aktuelle Alter basierend auf dem Geburtsdatum.
        """
        today = date.today()
        age = today.year - birthday_date.year
        if (today.month, today.day) < (birthday_date.month, birthday_date.day):
            age -= 1
        return age
