import discord
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
from utils.birthday_utils import BirthdayUtils


class BirthdayCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.birthday_utils = BirthdayUtils()
        self.task = None

    async def cog_load(self):
        # Diese Methode wird asynchron aufgerufen, sobald der Cog geladen wird,
        # sodass der Event-Loop zur Verfügung steht.
        self.task = asyncio.create_task(self.birthday_checker_loop())

    @commands.hybrid_command(name="setbirthday", description="Setze deinen Geburtstag. Format: TT.MM.JJJJ")
    async def set_birthday(self, ctx: commands.Context, member: discord.Member, birthday: str):
        """
        Mit diesem Befehl kann ein User seinen Geburtstag setzen.
        Falls versucht wird, einen anderen User zu setzen, dürfen das nur Administratoren.
        """
        if member != ctx.author and not ctx.author.guild_permissions.administrator:
            await ctx.send("Du darfst nur deinen eigenen Geburtstag setzen!")
            return

        response = self.birthday_utils.set_birthday(str(ctx.guild.id), str(member.id), birthday)
        await ctx.send(response)

    @commands.hybrid_command(name="viewbirthdays", description="Zeigt alle gesetzten Geburtstage mit Username an.")
    async def view_birthdays(self, ctx: commands.Context):
        """
        Listet alle in der aktuellen Guild gesetzten Geburtstage auf.
        Für jeden Eintrag wird der Username (oder die User-ID, falls der Member nicht mehr vorhanden ist)
        sowie das Datum (im Format TT.MM.JJJJ) angezeigt.
        """
        guild_birthdays = self.birthday_utils.birthdays.get(str(ctx.guild.id), {})
        if not guild_birthdays:
            await ctx.send("Es wurden noch keine Geburtstage gesetzt.")
            return

        result_lines = []
        for user_id, info in guild_birthdays.items():
            member = ctx.guild.get_member(int(user_id))
            name = member.display_name if member else f"Unbekannter User ({user_id})"
            try:
                # Datum wird vom ISO-Format "YYYY-MM-DD" in TT.MM.JJJJ konvertiert.
                bday = datetime.strptime(info["birthday"], "%Y-%m-%d").date()
                formatted_bday = bday.strftime("%d.%m.%Y")
            except Exception:
                formatted_bday = info["birthday"]
            result_lines.append(f"{name}: {formatted_bday}")

        message = "\n".join(result_lines)
        await ctx.send(f"**Gesetzte Geburtstage:**\n{message}")

    @commands.hybrid_command(name="deletebirthday", description="Löscht den gespeicherten Geburtstag eines Members.")
    async def delete_birthday(self, ctx: commands.Context, member: discord.Member):
        """
        Löscht den gespeicherten Geburtstag für den angegebenen Member.
        Nur der User selbst oder Administratoren dürfen diesen Befehl ausführen.
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
                             description="Bearbeite den gesetzten Geburtstag eines Members. Format: TT.MM.JJJJ")
    async def edit_birthday(self, ctx: commands.Context, member: discord.Member, new_birthday: str):
        """
        Bearbeitet den gespeicherten Geburtstag für den angegebenen Member.
        Nur der User selbst oder Administratoren dürfen einen Geburtstag bearbeiten.
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
        self.birthday_utils.save_birthdays()
        await ctx.send(f"Geburtstag für {member.display_name} wurde auf {bday.strftime('%d.%m.%Y')} aktualisiert.")

    @commands.hybrid_command(name="viewbirthday",
                             description="Zeigt den gesetzten Geburtstag eines bestimmten Members an.")
    async def view_birthday(self, ctx: commands.Context, member: discord.Member):
        """
        Zeigt den gesetzten Geburtstag des angegebenen Members an.
        Falls kein Geburtstag gesetzt wurde, wird eine entsprechende Nachricht ausgegeben.
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
        await ctx.send(f"{member.display_name} hat am {formatted_bday} geburtstag.")

    async def birthday_checker_loop(self):
        """
        Eine Endlosschleife, die einmal täglich zur Mitternacht (lokale Zeit) alle
        gespeicherten Geburtstage prüft und im entsprechenden Channel Glückwünsche postet.
        """
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            now = datetime.now()
            # Berechne die Sekunden bis zum nächsten Mitternacht.
            tomorrow = now.date() + timedelta(days=1)
            next_midnight = datetime.combine(tomorrow, datetime.min.time())
            seconds_until_midnight = (next_midnight - now).total_seconds()
            await asyncio.sleep(seconds_until_midnight)

            for guild in self.bot.guilds:
                birthday_list = self.birthday_utils.check_birthdays(str(guild.id))
                if birthday_list:
                    # Finde einen Channel, in den der Bot schreiben darf.
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
                        member = guild.get_member(int(user_id))
                        if member:
                            await channel.send(f"Alles Gute zum {age}ten Geburtstag {member.mention}🎉🎂 ")
                        else:
                            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(BirthdayCog(bot))
