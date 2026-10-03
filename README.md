# Music Bot

Discord music bot using discord.py + Wavelink + Lavalink.

## Commands

- `?play <Spotify playlist link>`
- `?skip`
- `?stop`
- `?ping`

## Railway

Run the bot and Lavalink as separate Railway services.

### Bot service variables

- `DISCORD_TOKEN`
- `LAVALINK_URI`
- `LAVALINK_PASSWORD`

### Lavalink service variables

- `LAVALINK_PASSWORD`
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`

The Lavalink service uses the configuration in `lavalink/application.yml`.
