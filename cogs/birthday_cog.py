import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
from utils.birthday_utils import BirthdayUtils


class BirthdayCog(commands.Cog):
    """
    Ein Discord Cog zur Verwaltung von Geburtstagen.
    Enthält Befehle zum Setzen, Ansehen, Bearbeiten und Löschen von Geburtstagen sowie einen
    Hintergrundtask, der täglich Geburtstagswünsche postet.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initialisiert den BirthdayCog und lädt die gespeicherten Geburtstage.

        :param bot: Die Instanz des Discord Bots.
        @return: None
        """
        self.bot = bot
        self.birthday_utils = BirthdayUtils()
        self.task = None

    async def cog_load(self):
        """
        Asynchrone Initialisierung, die den Hintergrundtask startet.

        :param: keine
        @return: None
        """
        self.task = asyncio.create_task(self.birthday_checker_loop())

    @commands.hybrid_command(name="setbirthday",
                             description="Setze deinen Geburtstag. Format: TT.MM.JJJJ. Optional: <name>")
    async def set_birthday(self, ctx: commands.Context, member: discord.Member, birthday: str, name: str = None):
        """
        Setzt den Geburtstag für einen Nutzer in der Guild. Optional kann ein Name angegeben werden;
        wird kein Name übergeben, so wird der aktuelle Discord-Username verwendet.

        :param ctx: Kontext des Befehls.
        :param member: Der Discord Member, dessen Geburtstag gesetzt werden soll.
        :param birthday: Das Geburtsdatum als string im Format TT.MM.JJJJ.
        :param name: Optionaler Name, der gespeichert wird.
        @return: Eine Bestätigungsmeldung als string.
        """
        if member != ctx.author and not ctx.author.guild_permissions.administrator:
            await ctx.send("Du darfst nur deinen eigenen Geburtstag setzen!")
            return

        if not name:
            name = member.display_name

        response = self.birthday_utils.set_birthday(str(ctx.guild.id), str(member.id), birthday, name)
        await ctx.send(response)

    @commands.hybrid_command(name="viewbirthdays", description="Zeigt alle gesetzten Geburtstage mit Username an.")
    async def view_birthdays(self, ctx: commands.Context):
        """
        Listet alle in der aktuellen Guild gespeicherten Geburtstage auf.

        :param ctx: Kontext des Befehls.
        @return: Eine Nachricht, die alle Geburtstage im Format 'Name: TT.MM.JJJJ' anzeigt.
        """
        guild_birthdays = self.birthday_utils.birthdays.get(str(ctx.guild.id), {})
        if not guild_birthdays:
            await ctx.send("Es wurden noch keine Geburtstage gesetzt.")
            return

        result_lines = []
        for user_id, info in guild_birthdays.items():
            member = ctx.guild.get_member(int(user_id))
            stored_name = info.get("name")
            name_to_show = stored_name if stored_name else (
                member.display_name if member else f"Unbekannter User ({user_id})")
            try:
                bday = datetime.strptime(info["birthday"], "%Y-%m-%d").date()
                formatted_bday = bday.strftime("%d.%m.%Y")
            except Exception:
                formatted_bday = info["birthday"]
            result_lines.append(f"{name_to_show}: {formatted_bday}")

        message = "\n".join(result_lines)
        await ctx.send(f"**Gesetzte Geburtstage:**\n{message}")

    @commands.hybrid_command(name="deletebirthday", description="Löscht den gespeicherten Geburtstag eines Members.")
    async def delete_birthday(self, ctx: commands.Context, member: discord.Member):
        """
        Löscht den gespeicherten Geburtstag eines Members.

        :param ctx: Kontext des Befehls.
        :param member: Der Discord Member, dessen Geburtstag gelöscht werden soll.
        @return: Eine Bestätigungsmeldung als string, sofern der Geburtstag gelöscht wurde.
        """
        if member != ctx.author and not ctx.author.guild_permissions.administrator:
            await ctx.send("Du darfst nur deinen eigenen Geburtstag löschen!")
            return

        guild_id = str(ctx.guild.id)
        user_id = str(member.id)
        if guild_id not in self.birthday_utils.birthdays or user_id not in self.birthday_utils.birthdays[guild_id]:
            await ctx.send("Für diesen User wurde kein Geburtstag gespeichert!")
            return

        del self.birthday_utils.birthdays[guild_id][user_id]
        self.birthday_utils.save_birthdays()
        await ctx.send(f"Geburtstag für {member.display_name} wurde gelöscht!")

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
        """
        Zeigt den gespeicherten Geburtstag eines bestimmten Members an.

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

    async def birthday_checker_loop(self):
        """
        Führt einmal täglich zur Mitternacht eine Überprüfung aller gespeicherten Geburtstage durch und postet
        entsprechende Glückwünsche in den jeweiligen Guild-Channels.

        :param: keine
        @return: None
        """
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = datetime.now()
            tomorrow = now.date() + timedelta(days=1)
            next_midnight = datetime.combine(tomorrow, datetime.min.time())
            seconds_until_midnight = (next_midnight - now).total_seconds()
            await asyncio.sleep(seconds_until_midnight)

            for guild in self.bot.guilds:
                birthday_list = self.birthday_utils.check_birthdays(str(guild.id))
                if birthday_list:
                    channel = guild.system_channel
                    if channel is None:
                        for ch in guild.text_channels:
                            if ch.permissions_for(guild.me).send_messages:
                                channel = ch
                                break
                    if channel is None:
                        continue

                    for user_id, bday in birthday_list:
                        age = self.birthday_utils.get_age(bday)
                        member_obj = guild.get_member(int(user_id))
                        if member_obj:
                            await channel.send(f"Alles Gute zum {age}ten Geburtstag {member_obj.mention}🎉🎂!")
                        else:
                            pass


async def setup(bot: commands.Bot):
    """
    Fügt diesen Cog dem Bot hinzu.

    :param bot: Die Instanz des Discord Bots.
    @return: None
    """
    await bot.add_cog(BirthdayCog(bot))
