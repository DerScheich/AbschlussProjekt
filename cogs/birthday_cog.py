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

    @commands.hybrid_command(name='viewbirthdays', description='Zeigt alle Geburtstag-Einträge sortiert an.')
    async def view_birthdays(self, ctx: commands.Context):
        """
        Zeigt gesetzte Geburtstage an (älteste zuerst).

        :param ctx: Command-Kontext.
        :return: None
        """
        guild_id = str(ctx.guild.id)
        data = self.birthday_utils.birthdays.get(guild_id, {})
        if not data:
            return await ctx.send('Keine Geburtstage gesetzt.')
        lines = []
        for uid, info in data.items():
            try:
                bd_str = datetime.strptime(info['birthday'], '%Y-%m-%d').strftime('%d.%m.%Y')
            except:
                bd_str = info['birthday']
            name = info.get('name') or ctx.guild.get_member(int(uid)).display_name
            lines.append(f'{name}: {bd_str}')
        await ctx.send('**Geburtstage:**\n' + '\n'.join(lines))

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
