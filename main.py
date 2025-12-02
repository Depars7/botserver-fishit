# bot.py
import discord
from discord.ext import commands
import aiohttp
import os
import asyncio

# Place ID Roblox yang digunakan (Fish-it)
ROBLOX_PLACE_ID = 121864768012064

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot online sebagai {bot.user}")

# --- Fungsi Global untuk Pengambilan Data ---
async def fetch_roblox_servers(place_id: int = ROBLOX_PLACE_ID, limit: int = 10):
    # ... (Kode fetch_roblox_servers yang sudah benar) ...
    url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=10&sortOrder=Desc&excludeFullGames=true"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    print(f"Roblox API returned status code: {resp.status}")
                    return None
                data = await resp.json()
                return data.get("data", [])[:limit]
        except aiohttp.ClientError as e:
            print(f"Aiohttp network error: {e}")
            return None
        except asyncio.TimeoutError:
            print("Request to Roblox API timed out.")
            return None
        except Exception as e:
            print(f"An unexpected error occurred during fetch: {e}")
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
        # ... (Kode get_embed yang sudah benar) ...
        if not self.servers:
            return discord.Embed(
                title="⚠️ Data Server Tidak Tersedia",
                description="Tidak ada data server yang valid saat ini.",
                color=discord.Color.red()
            )

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


@bot.command()
async def roblox(ctx):
    loading_message = await ctx.send("🔍 Mengambil data server...")

    servers = await fetch_roblox_servers(limit=10) 

    if not servers:
        return await loading_message.edit(content="❌ Tidak bisa mengambil data server Roblox atau tidak ada server ditemukan.")

    view = ServerPaginator(servers)
    await loading_message.edit(content=None, embed=view.get_embed(), view=view)

# Fungsi utama untuk menjalankan bot
async def start_bot():
    """Jalankan bot menggunakan token dari environment variable."""
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable not set.")
    await bot.start(token)

bot.run(os.environ.get("DISCORD_TOKEN"))
