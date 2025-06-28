import discord
import youtube_dl
import os

from typing import Optional, Any, Dict
from dotenv import load_dotenv

from discord.ext import commands
from discord.ext.commands import Context, Bot
from discord import (
    VoiceChannel,
    FFmpegPCMAudio,
    PCMVolumeTransformer,
)

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot: Bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_format_options: Dict[str, Any] = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options: Dict[str, Any] = {
    'options': '-vn',
}

ytdl: youtube_dl.YoutubeDL = youtube_dl.YoutubeDL(ytdl_format_options)


class YTDLSource(PCMVolumeTransformer):
    def __init__(
        self,
        source: FFmpegPCMAudio,
        *,
        data: Dict[str, Any],
        volume: float = 0.5
    ) -> None:
        super().__init__(source, volume)
        self.data: Dict[str, Any] = data
        self.title: str = data.get('title', 'Título Desconhecido')
        self.url: str = data.get('url', '')

    @classmethod
    async def from_url(
        cls,
        url: str,
        *,
        loop: Optional[discord.EventStatus] = None,
        stream: bool = False
    ) -> 'YTDLSource':
        loop = loop or discord.utils.get_running_loop()
        data: Dict[str, Any] = await loop.run_in_executor(
            None,
            lambda: ytdl.extract_info(
                url, 
                download=not stream
            )
        )

        if 'entries' in data:
            data = data['entries'][0]

        filename: str = (
            data['url'] if stream else ytdl.prepare_filename(data)
        )

        return cls(
            FFmpegPCMAudio(filename, **ffmpeg_options),
            data=data
        )


@bot.event
async def on_ready() -> None:
    print(f'Bot {bot.user} está online!')


@bot.command()
async def play(ctx: Context, *, url: str) -> None:
    if not ctx.author.voice:
        await ctx.send(
            'Você precisa estar em um canal de voz para usar esse comando!'
        )
        return

    channel: VoiceChannel = ctx.author.voice.channel

    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)

    async with ctx.typing():
        player: YTDLSource = await YTDLSource.from_url(
            url,
            loop=bot.loop,
            stream=True
        )
        ctx.voice_client.stop()
        ctx.voice_client.play(
            player,
            after=lambda e: print(f'Erro no player: {e}') if e else None
        )

    await ctx.send(f'Tocando: {player.title}')


@bot.command()
async def stop(ctx: Context) -> None:
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('Desconectado do canal de voz.')
    else:
        await ctx.send('Não estou conectado a nenhum canal de voz.')


@bot.command()
async def pause(ctx: Context) -> None:
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send('Pausado.')
    else:
        await ctx.send('Nada está tocando.')


@bot.command()
async def resume(ctx: Context) -> None:
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send('Retomado.')
    else:
        await ctx.send('A música não está pausada.')


@bot.command()
async def skip(ctx: Context) -> None:
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send('Música pulada.')
    else:
        await ctx.send('Nada está tocando.')


bot.run(token=os.getenv('token_bot_discord'))
