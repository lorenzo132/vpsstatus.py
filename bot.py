import discord
import asyncio
import psutil
import time
import os
import GPUtil
from discord.ext import commands
from datetime import datetime
from dotenv import load_dotenv
import platform
import subprocess

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
MESSAGE_ID = int(os.getenv("MESSAGE_ID"))
PREFIX = os.getenv("PREFIX")
OWNER_ID = int(os.getenv("OWNER_ID"))

intents = discord.Intents.default()
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# Format bytes to human-readable form
def format_bytes(size, decimal_places=2):
    if size == 0:
        return "0 Bytes"
    units = ["Bytes", "KB", "MB", "GB", "TB", "PB"]
    i = 0
    while size >= 1024 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.{decimal_places}f} {units[i]}"

# Format uptime in a readable format
def format_uptime(seconds):
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

# Function to get detailed CPU model
def get_cpu_model():
    try:
        # Check for CPU info on Linux or Mac
        if platform.system() == "Linux":
            return subprocess.check_output("lscpu | grep 'Model name'", shell=True).decode().strip().split(":")[1].strip()
        elif platform.system() == "Darwin":  # macOS
            return subprocess.check_output("sysctl -n machdep.cpu.brand_string", shell=True).decode().strip()
        else:  # Windows
            return platform.processor()  # Windows usually gives the CPU name
    except Exception as e:
        return "Unknown CPU"

# Fetch system stats
async def get_embed():
    cpu_name = get_cpu_model() or "Unknown CPU"
    cpu_usage = psutil.cpu_percent()
    cores = f"{psutil.cpu_count(logical=False)}P | {psutil.cpu_count(logical=True)}T"

    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    uptime = format_uptime(time.time() - psutil.boot_time())

    # Get GPU Info
    gpus = GPUtil.getGPUs()
    gpu_info = "No GPU detected"
    if gpus:
        gpu = gpus[0]  # Assuming a single GPU
        gpu_info = f"{gpu.name} | Usage: {gpu.memoryUsed}MB/{gpu.memoryTotal}MB"

    # Network Stats
    net_io = psutil.net_io_counters()
    net_sent = format_bytes(net_io.bytes_sent)
    net_recv = format_bytes(net_io.bytes_recv)
    
    # Calculate current transfer rate (sent/received in the last second)
    prev_net_io = psutil.net_io_counters()
    await asyncio.sleep(1)  # Sleep for 1 second to measure change
    curr_net_io = psutil.net_io_counters()

    transfer_sent = format_bytes(curr_net_io.bytes_sent - prev_net_io.bytes_sent)
    transfer_recv = format_bytes(curr_net_io.bytes_recv - prev_net_io.bytes_recv)

    stats_text = (
        f"CPU: {cpu_name}\n"
        f"CPU Usage: {cpu_usage:.2f}%\n"
        f"Cores: {cores}\n"
        f"-------------------------------------\n"
        f"Memory:\n"
        f"Current Usage: {format_bytes(memory.used)}/{format_bytes(memory.total)}\n"
        f"Available: {format_bytes(memory.available)}\n"
        f"-------------------------------------\n"
        f"Disk:\n"
        f"Current Usage: {format_bytes(disk.used)}/{format_bytes(disk.total)}\n"
        f"Free: {format_bytes(disk.free)}\n"
        f"-------------------------------------\n"
        f"GPU:\n"
        f"{gpu_info}\n"
        f"-------------------------------------\n"
        f"Network:\n"
        f"Transfer (Sent): {transfer_sent}\n"
        f"Transfer (Received): {transfer_recv}\n"

        f"Total Sent: {net_sent}\n"
        f"Total Received: {net_recv}\n"
        f"-------------------------------------\n"
        f"Uptime:\n"
        f"{uptime}\n"
        f"-------------------------------------\n"
    )

    # WebSocket ping as a separate code block
    discord_ping = f"{round(bot.latency * 1000)}ms"
    discord_ping_text = f"```yaml\n{discord_ping}\n```"

    embed = discord.Embed(title="Server Stats", color=0x3cfa5f, timestamp=datetime.utcnow())
    embed.add_field(name="Server Info", value=f"```yaml\n{stats_text}\n```", inline=False)
    embed.add_field(name="WebSocket Ping", value=discord_ping_text, inline=False)

    return embed

@bot.event
async def on_ready():
    print("Bot is ready")
    channel = bot.get_channel(CHANNEL_ID)
    message = await channel.fetch_message(MESSAGE_ID)

    async def update_stats():
        while True:
            embed = await get_embed()
            await message.edit(embed=embed)
            await asyncio.sleep(10)  # Update every 10 seconds

    bot.loop.create_task(update_stats())

@bot.command()
async def stats(ctx):
    embed = await get_embed()
    await ctx.send(embed=embed)

@bot.command()
async def eval(ctx, *, code: str):
    if ctx.author.id != OWNER_ID:
        return
    try:
        start_time = time.time()
        result = eval(code)
        if asyncio.iscoroutine(result):
            result = await result
        end_time = (time.time() - start_time) * 1000
        response = f"Output:\n```py\n{result}```\nType:```{type(result).__name__}```\n\n⏱️ `{end_time:.2f}ms`"
    except Exception as e:
        response = f"Error:```xl\n{e}\n```"
    await ctx.send(response)

bot.run(TOKEN)
