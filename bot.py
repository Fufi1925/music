import os
import discord
import wavelink
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
LAVALINK_URI = os.getenv("LAVALINK_URI", "http://localhost:2333")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing")
if not LAVALINK_PASSWORD:
    raise RuntimeError("LAVALINK_PASSWORD is missing")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


class MusicBot(commands.Bot):
    async def setup_hook(self):
        await wavelink.Pool.connect(
            nodes=[wavelink.Node(uri=LAVALINK_URI, password=LAVALINK_PASSWORD)],
            client=self,
        )


bot = MusicBot(command_prefix="?", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_wavelink_node_ready(payload: wavelink.NodeReadyEventPayload):
    print(f"Lavalink node ready: {payload.node.identifier}")


@bot.listen("on_wavelink_track_end")
async def on_track_end(payload: wavelink.TrackEndEventPayload):
    player = payload.player
    if player is None or player.queue.is_empty:
        return

    track = player.queue.get()
    await player.play(track)


@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")


@bot.command()
async def play(ctx, playlist_url: str):
    if not playlist_url.startswith(("https://open.spotify.com/", "http://open.spotify.com/")):
        await ctx.send("Bitte einen gültigen Spotify-Link senden.")
        return

    voice = getattr(ctx.author, "voice", None)
    if not voice or not voice.channel:
        await ctx.send("Du musst zuerst in einem Sprachkanal sein.")
        return

    try:
        player = ctx.guild.voice_client
        if player is None:
            player = await voice.channel.connect(cls=wavelink.Player)
        elif player.channel != voice.channel:
            await player.move_to(voice.channel)

        result = await wavelink.Playable.search(playlist_url)
        if not result:
            await ctx.send("Die Playlist konnte von Lavalink nicht geladen werden.")
            return

        if isinstance(result, wavelink.Playlist):
            tracks = result.tracks
            playlist_name = result.name or "Spotify-Playlist"
        else:
            tracks = list(result)
            playlist_name = "Spotify-Playlist"

        if not tracks:
            await ctx.send("Die Playlist enthält keine abspielbaren Tracks.")
            return

        player.queue.put(tracks)

        if not player.playing:
            await player.play(player.queue.get())

        await ctx.send(f"▶️ **{playlist_name}** — {len(tracks)} Tracks zur Queue hinzugefügt.")

    except Exception as e:
        print(f"Playback error: {e}")
        await ctx.send("Die Playlist konnte nicht gestartet werden. Prüfe die Lavalink-Verbindung.")


@bot.command()
async def skip(ctx):
    player = ctx.guild.voice_client
    if not isinstance(player, wavelink.Player) or not player.playing:
        await ctx.send("Es läuft gerade nichts.")
        return
    await player.skip()
    await ctx.send("⏭️ Übersprungen.")


@bot.command()
async def stop(ctx):
    player = ctx.guild.voice_client
    if not isinstance(player, wavelink.Player):
        await ctx.send("Ich bin nicht im Sprachkanal.")
        return
    player.queue.clear()
    await player.disconnect()
    await ctx.send("⏹️ Musik gestoppt.")


bot.run(DISCORD_TOKEN)
