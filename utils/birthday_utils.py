import json
from datetime import datetime, date
import os

BIRTHDAY_FILE = "birthdays.json"

class BirthdayUtils:
    """
    Verwaltet Geburtstage pro Guild mit Persistenz in JSON.
    """
    def __init__(self):
        """
        Lädt bestehende Geburtstage aus Datei.

        :return: None
        """
        self.birthdays = {}
        self.load_birthdays()

    def load_birthdays(self):
        """
        Lädt Geburtstage aus JSON-Datei, falls vorhanden.

        :return: None
        """
        if os.path.exists(BIRTHDAY_FILE):
            try:
                with open(BIRTHDAY_FILE, 'r') as f:
                    self.birthdays = json.load(f)
            except Exception as e:
                print(f"Error loading birthdays: {e}")

    def save_birthdays(self):
        """
        Speichert aktuelle Geburtstage in JSON-Datei.

        :return: None
        """
        try:
            with open(BIRTHDAY_FILE, 'w') as f:
                json.dump(self.birthdays, f, indent=4)
        except Exception as e:
            print(f"Error saving birthdays: {e}")

    def set_birthday(self, guild_id: str, user_id: str, birthday_str: str, name: str = None) -> str:
        """
        Speichert Geburtstag eines Users.

        :param guild_id: Guild-ID.
        :param user_id: User-ID.
        :param birthday_str: Datum TT.MM.JJJJ.
        :param name: Optionaler Anzeigename.
        :return: Bestätigungstext.
        """
        try:
            bday = datetime.strptime(birthday_str, '%d.%m.%Y').date()
        except ValueError:
            return "Ungültiges Datumsformat. Bitte verwende TT.MM.JJJJ."
        self.birthdays.setdefault(guild_id, {})
        if user_id in self.birthdays[guild_id]:
            return "Du hast bereits deinen Geburtstag gesetzt."
        self.birthdays[guild_id][user_id] = {
            'birthday': bday.strftime('%Y-%m-%d'),
            'name': name or '',
            'last_wished': None
        }
        self.save_birthdays()
        return (f"Geburtstag gesetzt auf {bday.strftime('%d.%m.%Y')}. "
                + (f"Name: {name}." if name else ""))

    def check_birthdays(self, guild_id: str):
        """
        Prüft, welche Nutzer heute Geburtstag haben und noch nicht gewünscht wurden.

        :param guild_id: Guild-ID.
        :return: Liste von (user_id, birthday_date).
        """
        today = date.today()
        birthday_users = []
        if guild_id not in self.birthdays:
            return birthday_users

        for user_id, info in self.birthdays[guild_id].items():
            try:
                bday = datetime.strptime(info['birthday'], '%Y-%m-%d').date()
                last = info.get('last_wished')
                if bday.month == today.month and bday.day == today.day:
                    if last is None or int(last) < today.year:
                        birthday_users.append((user_id, bday))
                        self.birthdays[guild_id][user_id]['last_wished'] = str(today.year)
            except Exception as e:
                print(f"Error processing birthday for {user_id}: {e}")
        if birthday_users:
            self.save_birthdays()
        return birthday_users

    def get_age(self, birthday_date: date) -> int:
        """
        Berechnet das Alter eines Nutzers basierend auf dem Geburtsdatum.

        :param birthday_date: Geburtsdatum als date.
        :return: Alter in Jahren.
        """
        today = date.today()
        age = today.year - birthday_date.year
        if (today.month, today.day) < (birthday_date.month, birthday_date.day):
            age -= 1
        return age