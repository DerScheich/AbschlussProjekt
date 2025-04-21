import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
from utils.birthday_utils import BirthdayUtils

class BirthdayCog(commands.Cog):
    """
    Cog zur Verwaltung von Geburtstagen und automatischen Grüßen.
    """
    def __init__(self, bot: commands.Bot):
        """
        Initialisiert Cog und lädt BirthdayUtils.

        :param bot: Bot-Instanz.
        :return: None
        """
        self.bot = bot
        self.birthday_utils = BirthdayUtils()
        self.task = None

    async def cog_load(self):
        """
        Startet den Hintergrundtask für tägliche Prüfungen.

        :return: None
        """
        self.task = asyncio.create_task(self.birthday_checker_loop())

    @commands.hybrid_command(name='setbirthday', description='Setze Geburtstag. Format: TT.MM.JJJJ. Optional: Name')
    async def set_birthday(self, ctx: commands.Context, member: discord.Member, birthday: str, name: str = None):
        """
        Setzt oder aktualisiert den Geburtstag eines Users.

        :param ctx: Command-Kontext.
        :param member: Discord Member.
        :param birthday: Datum TT.MM.JJJJ.
        :param name: Optionaler Anzeigename.
        :return: None
        """
        if member != ctx.author and not ctx.author.guild_permissions.administrator:
            return await ctx.send('Nur eigene Geburtstage setzen!')
        name = name or member.display_name
        resp = self.birthday_utils.set_birthday(str(ctx.guild.id), str(member.id), birthday, name)
        await ctx.send(resp)

    @commands.hybrid_command(name="editbirthday",
                             description="Bearbeite den gesetzten Geburtstag eines Members. Format: TT.MM.JJJJ. Optional: <new_name>")
    async def edit_birthday(self, ctx: commands.Context, member: discord.Member, new_birthday: str,
                            new_name: str = None):
            """
            Bearbeitet den gespeicherten Geburtstag eines Members. Es können sowohl das Geburtsdatum (Format: TT.MM.JJJJ) als auch
            der gespeicherte Name editiert werden. Wird kein neuer Name angegeben, bleibt der bisherige Name erhalten.

            :param ctx: Kontext des Befehls.
            :param member: Der Discord Member, dessen Geburtstag editiert werden soll.
            :param new_birthday: Das neue Geburtsdatum als string im Format TT.MM.JJJJ.
            :param new_name: Optional, neuer Name als string.
            @return: Eine Bestätigungsmeldung als string, sofern der Geburtstag (und ggf. der Name) aktualisiert wurde.
            """
            if member != ctx.author and not ctx.author.guild_permissions.administrator:
                await ctx.send("Du darfst nur deinen eigenen Geburtstag bearbeiten!")
                return

            guild_id = str(ctx.guild.id)
            user_id = str(member.id)
            if guild_id not in self.birthday_utils.birthdays or user_id not in self.birthday_utils.birthdays[guild_id]:
                await ctx.send("Für diesen User wurde noch kein Geburtstag gesetzt!")
                return

            try:
                bday = datetime.strptime(new_birthday, "%d.%m.%Y").date()
            except ValueError:
                await ctx.send("Ungültiges Datumsformat. Bitte verwende TT.MM.JJJJ.")
                return

            # Aktualisiere den Geburtstag und setze ggf. "last_wished" zurück.
            self.birthday_utils.birthdays[guild_id][user_id]["birthday"] = bday.strftime("%Y-%m-%d")
            self.birthday_utils.birthdays[guild_id][user_id]["last_wished"] = None

            if new_name is not None:
                # Überschreibe den bisherigen Namen mit dem neuen Namen
                self.birthday_utils.birthdays[guild_id][user_id]["name"] = new_name

            self.birthday_utils.save_birthdays()
            name_display = self.birthday_utils.birthdays[guild_id][user_id]["name"]
            await ctx.send(f"Geburtstag für {member.display_name} wurde auf {bday.strftime('%d.%m.%Y')} aktualisiert."
                           f"{' Neuer Name: ' + name_display if new_name is not None else ''}")

    @commands.hybrid_command(name="viewbirthday",
                             description="Zeigt den gesetzten Geburtstag eines bestimmten Members an.")
    async def view_birthday(self, ctx: commands.Context, member: discord.Member):
        """Zeigt den gespeicherten Geburtstag eines bestimmten Members an.

        :param ctx: Kontext des Befehls.
        :param member: Der Discord Member, dessen Geburtstag angezeigt werden soll.
        @return: Eine Nachricht, die den Namen und den Geburtstag (TT.MM.JJJJ) des Members anzeigt.
        """
        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        if guild_id not in self.birthday_utils.birthdays or user_id not in self.birthday_utils.birthdays[guild_id]:
            await ctx.send(f"Für {member.display_name} wurde kein Geburtstag gesetzt.")
            return
        info = self.birthday_utils.birthdays[guild_id][user_id]
        try:
            bday = datetime.strptime(info["birthday"], "%Y-%m-%d").date()
            formatted_bday = bday.strftime("%d.%m.%Y")
        except Exception:
            formatted_bday = info["birthday"]
        stored_name = info.get("name")
        name_to_show = stored_name if stored_name else member.display_name
        await ctx.send(f"Gesetzter Geburtstag für {name_to_show}: {formatted_bday}")

    @commands.hybrid_command(name="viewbirthdays",
                             description="Zeigt alle gesetzten Geburtstage mit Username an, von ältestem zum jüngsten.")
    async def view_birthdays(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)
        guild_birthdays = self.birthday_utils.birthdays.get(guild_id, {})

        if not guild_birthdays:
            await ctx.send("Es wurden noch keine Geburtstage gesetzt.")
            return

        # Liste aller Geburtstage sammeln mit Datum und Name
        items = []  # List of (birthday_date, display_name)
        for user_id, info in guild_birthdays.items():
            # Name bestimmen
            member = ctx.guild.get_member(int(user_id))
            stored_name = info.get("name")
            name_to_show = stored_name if stored_name else (
                member.display_name if member else f"Unbekannter User ({user_id})"
            )
            # Datum parsen
            try:
                bday_date = datetime.strptime(info["birthday"], "%Y-%m-%d").date()

            except Exception:
                continue
            items.append((bday_date, name_to_show))

        # Sortieren: älteste Geburtstage (kleinste Jahreszahl) zuerst
        items.sort(key=lambda x: x[0])

        # Ausgabe vorbereiten
        result_lines = [f"{name}: {bday.strftime('%d.%m.%Y')}" for bday, name in items]
        message = "\n".join(result_lines)
        await ctx.send(f"**Gesetzte Geburtstage:**\n{message}")

    @commands.hybrid_command(name='deletebirthday', description='Löscht einen Geburtstag.')
    async def delete_birthday(self, ctx: commands.Context, member: discord.Member):
        """
        Löscht den Geburtstag eines Users.

        :param ctx: Command-Kontext.
        :param member: Discord Member.
        :return: None
        """
        if member != ctx.author and not ctx.author.guild_permissions.administrator:
            return await ctx.send('Nur eigene löschen!')
        guild_id, uid = str(ctx.guild.id), str(member.id)
        if uid not in self.birthday_utils.birthdays.get(guild_id, {}):
            return await ctx.send('Kein Eintrag gefunden.')
        del self.birthday_utils.birthdays[guild_id][uid]
        self.birthday_utils.save_birthdays()
        await ctx.send(f'Geburtstag von {member.display_name} gelöscht.')

    async def birthday_checker_loop(self):
        """
        Hintergrundtask, der täglich um Mitternacht Geburtstagsgrüße sendet.

        :return: None
        """
        await self.bot.wait_until_ready()
        while True:
            now = datetime.now()
            tomorrow = now.date() + timedelta(days=1)
            until = datetime.combine(tomorrow, datetime.min.time())
            await asyncio.sleep((until - now).total_seconds())
            for guild in self.bot.guilds:
                wishes = self.birthday_utils.check_birthdays(str(guild.id))
                if not wishes: continue
                channel = guild.system_channel or next((ch for ch in guild.text_channels if ch.permissions_for(guild.me).send_messages), None)
                if not channel: continue
                for uid, bday in wishes:
                    age = self.birthday_utils.get_age(bday)
                    member = guild.get_member(int(uid))
                    if member:
                        await channel.send(f'Alles Gute zum {age}. Geburtstag, {member.mention}! 🎉🎂')

async def setup(bot: commands.Bot):
    """
    Registriert den BirthdayCog.

    :param bot: Bot-Instanz.
    :return: None
    """
    await bot.add_cog(BirthdayCog(bot))
