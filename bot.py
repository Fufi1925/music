import os
import re
import discord
from discord.ext import commands
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_TOKEN is missing")
if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
    raise RuntimeError("SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET is missing")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="?", intents=intents)

spotify = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=SPOTIFY_CLIENT_ID,
        client_secret=SPOTIFY_CLIENT_SECRET,
    )
)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.command()
async def ping(ctx):
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")

@bot.command()
async def play(ctx, playlist_url: str):
    match = re.search(r"playlist/([A-Za-z0-9]+)", playlist_url)
    if not match:
        await ctx.send("Bitte einen gültigen Spotify-Playlist-Link senden.")
        return

    playlist_id = match.group(1)

    try:
        playlist = spotify.playlist(playlist_id, fields="name,tracks.total")
        results = spotify.playlist_items(
            playlist_id,
            fields="items(track(name,artists(name))),next",
            additional_types=("track",),
        )

        tracks = []
        while True:
            for item in results["items"]:
                track = item.get("track")
                if track:
                    artists = ", ".join(a["name"] for a in track["artists"])
                    tracks.append(f"{track['name']} — {artists}")

            if not results["next"]:
                break
            results = spotify.next(results)

        if not tracks:
            await ctx.send("Die Playlist enthält keine lesbaren Tracks.")
            return

        preview = "\n".join(f"{i}. {track}" for i, track in enumerate(tracks[:10], 1))
        more = f"\n... und {len(tracks) - 10} weitere." if len(tracks) > 10 else ""
        await ctx.send(f"**{playlist['name']}**\n{preview}{more}")

    except Exception as e:
        print(f"Spotify error: {e}")
        await ctx.send("Die Spotify-Playlist konnte nicht geladen werden.")

bot.run(DISCORD_TOKEN)
