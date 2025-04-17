import discord
from discord.ext import commands

class HelpCog(commands.Cog):
    """
    Cog für den /help-Befehl, zeigt eine Übersicht aller verfügbaren Befehle an.

    :param bot: Die Bot-Instanz, zu der der Cog gehört.
    :type bot: commands.Bot
    :return: None
    """

    @commands.hybrid_command(name="help", description="Zeigt eine Übersicht aller Befehle an.")
    async def help(self, ctx: commands.Context):
        """
        Zeigt eine Übersicht aller Befehle an.

        :param ctx: Der Kontext, in dem der Befehl aufgerufen wurde.
        :type ctx: commands.Context
        :return: None
        """
        embed = discord.Embed(
            title="**Hilfe Übersicht**",
            color=discord.Color.blue(),
            description="Hier findest du alle verfügbaren Befehle."
        )
        embed.set_footer(text="Diese Nachricht ist nur für dich sichtbar.")

        embed.add_field(
            name="🟦 **Chat-Modus**", inline=False,
            value=(
                "**/ape** `<username>` [laut] – Imitationsmodus aktivieren\n"
                "**/noape** `<username>` – Imitationsmodus deaktivieren\n"
                "**/maggus** – Markus‑Rühl‑Stil aktivieren\n"
                "**/nomaggus** – Markus‑Rühl‑Stil deaktivieren\n"
                "**@mention** `<Nachricht>` – GPT-Chat und Geburtstags‑Intents"
            )
        )

        embed.add_field(
            name="🟨 **Audio-Effekte**", inline=False,
            value=(
                "**/slowed** `<input_audio>` [slow_factor] – Audio verlangsamen\n"
                "**/slowed_reverb** `<input_audio>` `<impulse_audio>` [slow_factor] – Reverb + Slowed\n"
                "**/reverb** `<input_audio>` `<impulse_audio>` – Nur Reverb\n"
                "**/stereo** `<input_audio>` – Mono → Stereo (Haas-Effekt)\n"
                "**/mono** `<input_audio>` – Stereo → Mono"
            )
        )

        embed.add_field(
            name="🟧 **Grafik**", inline=False,
            value=(
                "**/watermark** `<input_file>` `<watermark_file>` [position] [scale] [transparency] – Wasserzeichen hinzufügen\n"
                "**/sw** `<input_file>` – Bild/Video in Schwarz‑Weiß konvertieren"
            )
        )

        embed.add_field(
            name="🟥 **Bildprüfung**", inline=False,
            value=(
                "**/check** `<Bilddatei>` `<prompt>` – Bild mit GPT prüfen"
            )
        )

        embed.add_field(
            name="🟩 **Geburtstag**", inline=False,
            value=(
                "**/setbirthday** `<username>` `<TT.MM.JJJJ>` [Name] – Geburtstag setzen\n"
                "**/viewbirthdays** – Alle Geburtstage anzeigen\n"
                "**/viewbirthday** `<username>` – Geburtstag eines Users anzeigen\n"
                "**/editbirthday** `<username>` `<TT.MM.JJJJ>` [Neuer_Name] – Geburtstag bearbeiten\n"
                "**/deletebirthday** `<username>` – Geburtstag löschen"
            )
        )

        embed.add_field(
            name="🟪 **Musiksteuerung**", inline=False,
            value=(
                "**/play** `<Link>` – Song abspielen\n"
                "**/queue** – Warteschlange anzeigen\n"
                "**/skip** [Anzahl] – Song(s) überspringen\n"
                "**/clear_queue** – Warteschlange leeren\n"
                "**/pause** – Wiedergabe pausieren\n"
                "**/resume** – Wiedergabe fortsetzen\n"
                "**/stop** – Wiedergabe stoppen"
            )
        )

        await ctx.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    """
    Lädt den HelpCog in die Bot-Instanz.

    :param bot: Die Bot-Instanz, zu der der Cog hinzugefügt wird.
    :type bot: commands.Bot
    :return: None
    """
    bot.remove_command("help")
    await bot.add_cog(HelpCog(bot))
