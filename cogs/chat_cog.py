import discord
from discord.ext import commands
from utils.chat_utils import ChatUtils
from utils.birthday_utils import BirthdayUtils
from datetime import datetime, date
import json

MAX_HISTORY = 10

class ChatCog(commands.Cog):
    """
    Cog für allgemeinen Chat, Imitationsmodus und Geburtstagsabfragen.
    """
    def __init__(self, bot: commands.Bot):
        """
        Initialisiert Chat- und Utility-Instanzen.

        :param bot: Discord Bot-Instanz.
        :return: None
        """
        self.bot = bot
        self.mimic_users = {}
        self.maggus_mode = False
        self.chat_history = {}
        self.chat_utils = ChatUtils(maggus_mode=self.maggus_mode)
        self.birthday_utils = BirthdayUtils()
        self.ai_client = self.chat_utils.gpt_client

    @commands.hybrid_command(name="ape", description="Aktiviere Imitationsmodus für einen Benutzer.")
    async def ape(self, ctx: commands.Context, member: discord.Member, laut: bool = False):
        """
        Schaltet Imitationsmodus für den angegebenen Nutzer ein.

        :param ctx: Command-Kontext.
        :param member: Zu imitierender Nutzer.
        :param laut: Wenn True, mit TTS ausgeben.
        :return: None
        """
        # Imitationsmodus aktivieren
        self.mimic_users[member.id] = laut
        await ctx.send(f"Imitationsmodus für **{member.display_name}** aktiviert (TTS: {laut}).", ephemeral=True)

    @commands.hybrid_command(name="noape", description="Deaktiviere Imitationsmodus für einen Benutzer.")
    async def noape(self, ctx: commands.Context, member: discord.Member):
        """
        Schaltet Imitationsmodus für den angegebenen Nutzer aus.

        :param ctx: Command-Kontext.
        :param member: Nutzer.
        :return: None
        """
        # Imitationsmodus deaktivieren
        if member.id in self.mimic_users:
            self.mimic_users.pop(member.id)
            await ctx.send(f"Imitationsmodus für **{member.display_name}** deaktiviert.", ephemeral=True)
        else:
            await ctx.send(f"{member.display_name} war nicht im Imitationsmodus.", ephemeral=True)

    @commands.hybrid_command(name="maggus", description="Aktiviere Markus-Rühl-Stil für Antworten.")
    async def maggus(self, ctx: commands.Context):
        """
        Schaltet den Markus-Rühl-Stil ein.

        :param ctx: Command-Kontext.
        :return: None
        """
        # Stil aktivieren
        self.maggus_mode = True
        self.chat_utils.maggus_mode = True
        await ctx.send("Markus-Rühl-Stil aktiviert.", ephemeral=True)

    @commands.hybrid_command(name="nomaggus", description="Deaktiviere Markus-Rühl-Stil.")
    async def nomaggus(self, ctx: commands.Context):
        """
        Schaltet den Markus-Rühl-Stil aus.

        :param ctx: Command-Kontext.
        :return: None
        """
        # Stil deaktivieren
        self.maggus_mode = False
        self.chat_utils.maggus_mode = False
        await ctx.send("Markus-Rühl-Stil deaktiviert.", ephemeral=True)

    def get_sorted_upcoming(self, guild_id: str):
        """
        Liefert sortierte Geburtstage mit Datum und Alter.

        :param guild_id: Guild-ID als String.
        :return: Liste von (user_id, Name, Datum, Alter).
        """
        today = date.today()
        entries = self.birthday_utils.birthdays.get(guild_id, {})
        items = []
        # Geburtstage durchsuchen
        for uid, info in entries.items():
            try:
                bd = datetime.strptime(info['birthday'], '%Y-%m-%d').date()
            except:
                continue
            this_year = bd.replace(year=today.year)
            if this_year < today:
                next_bd = this_year.replace(year=today.year + 1)
            else:
                next_bd = this_year
            age_next = next_bd.year - bd.year
            name = info.get('name') or None
            items.append((uid, name, next_bd, age_next))
        items.sort(key=lambda x: x[2])
        return items

    def classify_birthday_intent(self, text: str) -> dict:
        """
        Analysiert Text auf Geburtstags-Intent via GPT.

        :param text: Eingabe-Text.
        :return: Dict mit intent, name oder ordinal.
        """
        # GPT-Intent-Klassifikation
        instructions = (
            "Erkenne Geburtstags-Intents (nächster, spezifisch, nach Name).\n"
            "Antworte JSON mit: intent: next_birthday|specific_birthday|after_birthday|none;\n"
            "name: (bei specific_birthday oder after_birthday); ordinal: (bei next_birthday).\n"
            "Beispiele:\n"
            "Input: 'Wer hat als nächstes Geburtstag?' Output: {\"intent\":\"next_birthday\",\"ordinal\":1}\n"
            "Input: 'Wer hat als übernächstes Geburtstag?' Output: {\"intent\":\"next_birthday\",\"ordinal\":2}\n"
            "Input: 'Wer hat als letztes Geburtstag im Jahr?' Output: {\"intent\":\"next_birthday\",\"ordinal\":\"last\"}\n"
            "Input: 'Wann hat Alice Geburtstag?' Output: {\"intent\":\"specific_birthday\",\"name\":\"Alice\"}\n"
            "Input: 'Wer hat nach Alice Geburtstag?' Output: {\"intent\":\"after_birthday\",\"name\":\"Alice\"}\n"
            "Input: 'Hi, wie geht's?' Output: {\"intent\":\"none\"}\n"
        )
        try:
            response = self.ai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": text},
                ],
                max_tokens=150,
            )
            data = json.loads(response.choices[0].message.content.strip())
            ordv = data.get("ordinal")
            if isinstance(ordv, str) and ordv.isdigit():
                data["ordinal"] = int(ordv)
            return data
        except Exception:
            return {"intent": "none"}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Listener für Nachrichten: Imitation, Geburtstage, allgemeiner Chat.

        :param message: Eintreffende Nachricht.
        :return: None
        """
        if message.author.bot:
            return

        # Imitationsmodus
        if message.author.id in self.mimic_users:
            await message.channel.send(
                self.chat_utils.ape_transform(message.content),
                tts=self.mimic_users[message.author.id]
            )
            return

        # Bot-Mention prüfen
        if self.bot.user in message.mentions:
            channel_id = message.channel.id

            # 1. Check-Kontext aus CheckCog holen
            check_cog = self.bot.get_cog("CheckCog")
            check_context = ""
            if check_cog:
                check_data = check_cog.memory.get(channel_id)
                if check_data:
                    # Füge sowohl Prompt als auch Ergebnis hinzu
                    check_context = (
                        f"\n[System: Vorheriger Check-Kontext] "
                        f"Frage: {check_data['prompt']} "
                        f"Antwort: {check_data['result']}"
                    )

            # 2. Geburtstags-Intent analysieren
            text = message.content
            gid = str(message.guild.id)
            intent = self.classify_birthday_intent(text)

            # 2a. Spezifischer Geburtstag
            if intent['intent'] == 'specific_birthday':
                query = intent.get('name', '').lower()
                for uid, info in self.birthday_utils.birthdays.get(gid, {}).items():
                    nm = info.get('name') or (
                        message.guild.get_member(int(uid)).display_name
                        if message.guild.get_member(int(uid)) else ''
                    )
                    if nm.lower() == query:
                        bd = info['birthday']
                        try:
                            d = datetime.strptime(bd, '%Y-%m-%d').strftime('%d.%m.%Y')
                        except:
                            d = bd
                        await message.channel.send(f"{nm} hat Geburtstag am {d}. 🎂")
                        return
                await message.channel.send(f"Keinen Geburtstag für '{query}' gefunden.")
                return

            # 2b. Nächster Geburtstag
            if intent['intent'] == 'next_birthday':
                sorted_list = self.get_sorted_upcoming(gid)
                if not sorted_list:
                    await message.channel.send("Es sind keine Geburtstage gespeichert.")
                    return
                ordv = intent.get('ordinal', 1)
                if ordv == 'last':
                    idx = len(sorted_list) - 1
                else:
                    idx = max(0, int(ordv) - 1) if isinstance(ordv, int) else 0
                uid, name, bd_date, age = sorted_list[idx]
                member = message.guild.get_member(int(uid))
                disp = name or (member.display_name if member else f"<@{uid}>")
                dstr = bd_date.strftime('%d.%m.%Y')
                label = {1: 'Nächster', 2: 'Übernächster'}.get(ordv, 'Letzter' if ordv == 'last' else 'Nächster')
                await message.channel.send(
                    f"{label} Geburtstag ist am {dstr} von {disp}. Dann wird er/sie {age} Jahre alt! 🎉"
                )
                return

            # 2c. Geburtstag nach Name
            if intent['intent'] == 'after_birthday':
                ref = intent.get('name', '').lower()
                sorted_list = self.get_sorted_upcoming(gid)
                ref_idx = next(
                    (i for i, (uid, name, bd, age) in enumerate(sorted_list)
                     if (name or message.guild.get_member(int(uid)).display_name).lower() == ref),
                    None
                )
                if ref_idx is None:
                    await message.channel.send(f"Keinen Geburtstag für '{ref}' gefunden.")
                    return
                next_idx = (ref_idx + 1) % len(sorted_list)
                uid, name, bd, age = sorted_list[next_idx]
                member = message.guild.get_member(int(uid))
                disp = name or (member.display_name if member else f"<@{uid}>")
                dstr = bd.strftime('%d.%m.%Y')
                await message.channel.send(
                    f"Nach {ref.capitalize()} kommt als nächstes {disp} am {dstr}. Dann wird er/sie {age} Jahre alt! 🎈"
                )
                return

            # 3. Fallback auf GPT-Chat mit Check-Kontext
            current_prompt = message.content + check_context
            if channel_id not in self.chat_history:
                self.chat_history[channel_id] = []
            self.chat_history[channel_id].append({
                "role": "user",
                "content": current_prompt
            })
            if len(self.chat_history[channel_id]) > MAX_HISTORY:
                self.chat_history[channel_id] = self.chat_history[channel_id][-MAX_HISTORY:]
            conversation_prompt = "\n".join(
                f"{msg['role']}: {msg['content']}"
                for msg in self.chat_history[channel_id]
            )
            answer = self.chat_utils.gpt_response(conversation_prompt)
            await message.channel.send(answer)
            self.chat_history[channel_id].append({
                "role": "assistant",
                "content": answer
            })
            return

async def setup(bot: commands.Bot):
    """
    Registriert den ChatCog.

    :param bot: Bot-Instanz.
    :return: None
    """
    await bot.add_cog(ChatCog(bot))
