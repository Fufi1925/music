import asyncio
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
        asyncio.create_task(self.connect_lavalink())

    async def connect_lavalink(self):
        while True:
            try:
                if any(node.status == wavelink.NodeStatus.CONNECTED for node in wavelink.Pool.nodes.values()):
                    return
                node = wavelink.Node(
                    uri=LAVALINK_URI,
                    password=LAVALINK_PASSWORD,
                    identifier="railway-lavalink",
                )
                print(f"Connecting to Lavalink at {LAVALINK_URI}...")
                await wavelink.Pool.connect(nodes=[node], client=self)
                print("Lavalink connection established.")
                return
            except Exception as exc:
                print(f"Lavalink unavailable: {exc}")
                await asyncio.sleep(10)


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
    await player.play(player.queue.get())


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
        node = wavelink.Pool.get_node()
        if node is None or node.status != wavelink.NodeStatus.CONNECTED:
            await ctx.send("Lavalink ist noch nicht bereit.")
            return

        player = ctx.guild.voice_client
        if player is None:
            player = await voice.channel.connect(cls=wavelink.Player)
        elif player.channel != voice.channel:
            await player.move_to(voice.channel)

        result = await wavelink.Playable.search(playlist_url)
        if not result:
            await ctx.send("Die Playlist konnte nicht geladen werden.")
            return

        if isinstance(result, wavelink.Playlist):
            tracks = list(result.tracks)
            playlist_name = result.name or "Spotify-Playlist"
        else:
            tracks = list(result)
            playlist_name = "Spotify-Playlist"

        if not tracks:
            await ctx.send("Keine abspielbaren Tracks gefunden.")
            return

        player.queue.put(tracks)

        if not player.playing:
            await player.play(player.queue.get())

        await ctx.send(f"**{playlist_name}** — {len(tracks)} Tracks hinzugefügt.")

    except Exception as e:
        print(f"Playback error: {e}")
        await ctx.send("Die Playlist konnte nicht gestartet werden.")


@bot.command()
async def skip(ctx):
    player = ctx.guild.voice_client
    if not isinstance(player, wavelink.Player) or not player.playing:
        await ctx.send("Es läuft gerade nichts.")
        return
    await player.skip()
    await ctx.send("Übersprungen.")


@bot.command()
async def stop(ctx):
    player = ctx.guild.voice_client
    if not isinstance(player, wavelink.Player):
        await ctx.send("Ich bin nicht im Sprachkanal.")
        return
    player.queue.clear()
    await player.disconnect()
    await ctx.send("Musik gestoppt.")


bot.run(DISCORD_TOKEN)
