import discord
from discord.ext import commands
import aiohttp
import os
import asyncio
from flask import Flask
import concurrent.futures
import logging

# Setel logging Flask agar tidak terlalu banyak pesan di konsol
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR) 

# --- Konfigurasi Bot dan Place ID ---
ROBLOX_PLACE_ID = 121864768012064
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents) 

@bot.event
async def on_ready():
    """Event yang dipanggil saat bot berhasil terhubung."""
    print(f"Bot online sebagai {bot.user}")

# --- Fungsi Global untuk Pengambilan Data ---
# FIX: Mengubah ROBLBOX_PLACE_ID menjadi ROBLOX_PLACE_ID
async def fetch_roblox_servers(place_id: int = ROBLOX_PLACE_ID, limit: int = 10):
    """Mengambil data server publik untuk ID tempat Roblox tertentu."""
    url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=10&sortOrder=Desc&excludeFullGames=true"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                return data.get("data", [])[:limit]
        except (aiohttp.ClientError, asyncio.TimeoutError, Exception):
            return None

# --- Kelas ServerPaginator (View) ---
class ServerPaginator(discord.ui.View):
    def __init__(self, servers):
        super().__init__(timeout=600)
        self.servers = servers
        self.page = 0
        self.join_button = discord.ui.Button(
            label="🔗 Join",
            style=discord.ButtonStyle.link,
            url="https://roblox.com"
        )
        self.add_item(self.join_button)

    async def refresh_servers(self):
        return await fetch_roblox_servers(limit=len(self.servers))

    def get_embed(self):
        """Membuat dan mengembalikan embed untuk halaman saat ini."""
        if not self.servers:
            return discord.Embed(title="⚠️ Data Server Tidak Tersedia", color=discord.Color.red())

        server = self.servers[self.page]
        server_id = server.get("id", "Unknown")
        playing = server.get("playing", 0)
        maxPlayers = server.get("maxPlayers", 0)
        ping = server.get("ping") or "Unavailable"
        fps = server.get("fps") or "Unavailable"

        self.join_button.url = f"https://www.roblox.com/games/start?placeId={ROBLOX_PLACE_ID}&serverId={server_id}"

        embed = discord.Embed(
            title=f"🎣 Server Public Fish-it ({self.page+1}/{len(self.servers)})",
            color=0x57F287
        )
        embed.add_field(name="Server ID", value=f"`{server_id}`", inline=False)
        embed.add_field(name="Players", value=f"**{playing}**/{maxPlayers}", inline=True)
        embed.add_field(name="Ping", value=f"{ping}", inline=True)
        embed.add_field(name="FPS", value=f"{fps}", inline=True)
        embed.set_footer(text=f"Total: {len(self.servers)} server | Timeout: 10 menit")

        return embed

    @discord.ui.button(label="⬅ Prev", style=discord.ButtonStyle.secondary, custom_id="prev_button")
    async def prev(self, interaction: discord.Interaction, button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.secondary, custom_id="next_button")
    async def next(self, interaction: discord.Interaction, button):
        if self.page < len(self.servers) - 1:
            self.page += 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.success, custom_id="refresh_button")
    async def refresh(self, interaction: discord.Interaction, button):
        await interaction.response.defer()
        new_servers = await self.refresh_servers()
        if not new_servers:
            return await interaction.followup.send("⚠️ Gagal refresh data.", ephemeral=True)
        self.servers = new_servers
        self.page = 0 
        await interaction.message.edit(embed=self.get_embed(), view=self)

@bot.command(name="server") 
async def server_command(ctx):
    """Command /server untuk menampilkan daftar server publik."""
    loading_message = await ctx.send("🔍 Mengambil data server...")
    servers = await fetch_roblox_servers(limit=10) 
    if not servers:
        return await loading_message.edit(content="❌ Tidak bisa mengambil data server Roblox atau tidak ada server ditemukan.")
    view = ServerPaginator(servers)
    await loading_message.edit(content=None, embed=view.get_embed(), view=view)


# --- HEALTH CHECK SERVER (Flask) ---
app = Flask(__name__)

@app.route('/')
def home():
    """Mengembalikan 200 OK untuk health check Koyeb."""
    return "Discord Bot is Running!", 200

def start_web_server():
    """Mulai server Flask."""
    port = int(os.environ.get("PORT", 8000)) 
    print(f"Starting web server for health check on port {port}")
    # app.run() adalah blocking, dijalankan di executor
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

async def start_bot_async():
    """Wrapper asinkron untuk bot.start."""
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("FATAL ERROR: DISCORD_TOKEN environment variable not set. Bot will not connect.")
        await asyncio.sleep(3600) 
    else:
        try:
            await bot.start(token)
        except discord.LoginFailure:
            print("ERROR: Invalid Discord token provided.")
        except Exception as e:
            print(f"An error occurred while running the bot: {e}")


# --- MAIN EXECUTION ---
def main():
    """Mengatur dan menjalankan bot dan web server secara bersamaan."""
    
    loop = asyncio.get_event_loop()
    
    # 1. Executor untuk menjalankan Flask (operasi blocking)
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    
    # 2. Web server (Blocking) dijalankan di thread terpisah (executor)
    web_task = loop.run_in_executor(executor, start_web_server)
    
    # 3. Bot Discord (Async) dijalankan di main event loop
    bot_task = loop.create_task(start_bot_async())

    # 4. Jalankan kedua tugas secara bersamaan.
    try:
        loop.run_until_complete(asyncio.gather(bot_task, web_task))
    except KeyboardInterrupt:
        print("Bot stopped by user.")
    except Exception as e:
        print(f"Main execution failed: {e}")
    finally:
        executor.shutdown(wait=False)
        
if __name__ == '__main__':
    main()

bot.run(os.environ.get("DISCORD_TOKEN"))
