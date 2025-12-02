from flask import Flask
from threading import Thread
import discord
from discord.ext import commands
import aiohttp
import os
import asyncio # Diperlukan untuk penanganan asinkron yang lebih baik

# Create a Flask app instance
app = Flask(__name__)

# Define a simple health check route
@app.route('/')
def home():
    return "Bot is running!", 200

# Function to run Flask in a separate thread
def run_server():
    # Use the port specified by the environment (often 8000 for Koyeb)
    port = int(os.environ.get("PORT", 8000)) 
    # Important: host='0.0.0.0' makes it accessible externally
    app.run(host='0.0.0.0', port=port)

class ServerPaginator(...):
    # ... your existing class code ...

# Before bot.run(...), start the web server in a background thread
if __name__ == '__main__':
    # 1. Start the Flask server in a non-blocking thread
    t = Thread(target=run_server)
    t.start()
    
    # 2. Start the Discord bot (main process)
    bot.run(os.environ.get("DISCORD_TOKEN"))

# Konfigurasi Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Place ID Roblox yang digunakan (Fish-it)
ROBLOX_PLACE_ID = 121864768012064

@bot.event
async def on_ready():
    """Event yang dipanggil saat bot berhasil terhubung."""
    print(f"Bot online sebagai {bot.user}")

# --- Fungsi Global untuk Pengambilan Data ---
async def fetch_roblox_servers(place_id: int = ROBLOX_PLACE_ID, limit: int = 10):
    """
    Mengambil data server publik untuk ID tempat Roblox tertentu.
    Menggunakan limit=100 di URL lalu memotongnya menjadi 'limit' untuk memastikan data terbaru.
    """
    url = f"https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=10&sortOrder=Desc&excludeFullGames=true"
    
    # Membuat sesi aiohttp baru setiap kali.
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, timeout=10) as resp:
                if resp.status != 200:
                    print(f"Roblox API returned status code: {resp.status}")
                    return None
                
                data = await resp.json()
                # Memotong data yang diterima sesuai batas yang diminta
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
        super().__init__(timeout=600) # Timeout ditingkatkan menjadi 10 menit
        
        self.servers = servers
        self.page = 0

        # Tombol Join (link diperbarui secara dinamis)
        self.join_button = discord.ui.Button(
            label="🔗 Join",
            style=discord.ButtonStyle.link,
            url="https://roblox.com" # Placeholder
        )
        self.add_item(self.join_button)

    async def refresh_servers(self):
        """Memanggil fungsi global untuk mendapatkan data server baru."""
        return await fetch_roblox_servers(limit=len(self.servers))

    def get_embed(self):
        """Membuat dan mengembalikan embed untuk halaman saat ini."""
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

        # Memperbarui URL tombol join
        self.join_button.url = f"https://www.roblox.com/games/start?placeId={ROBLOX_PLACE_ID}&serverId={server_id}"

        embed = discord.Embed(
            title=f"🎣 Server Public Fish-it ({self.page+1}/{len(self.servers)})",
            color=0x57F287 # Warna Discord Green
        )
        embed.add_field(name="Server ID", value=f"`{server_id}`", inline=False)
        embed.add_field(name="Players", value=f"**{playing}**/{maxPlayers}", inline=True)
        embed.add_field(name="Ping", value=f"{ping}", inline=True)
        embed.add_field(name="FPS", value=f"{fps}", inline=True)
        
        embed.set_footer(text=f"Total: {len(self.servers)} server | Timeout: 10 menit")

        return embed

    @discord.ui.button(label="⬅ Prev", style=discord.ButtonStyle.secondary, custom_id="prev_button")
    async def prev(self, interaction: discord.Interaction, button):
        """Tombol untuk pindah ke halaman sebelumnya."""
        if self.page > 0:
            self.page -= 1
            # Edit pesan karena ini adalah interaksi non-deferred
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("Ini sudah halaman pertama, klik **Refresh** untuk mendapatkan server baru.", ephemeral=True)

    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.secondary, custom_id="next_button")
    async def next(self, interaction: discord.Interaction, button):
        """Tombol untuk pindah ke halaman berikutnya."""
        if self.page < len(self.servers) - 1:
            self.page += 1
            # Edit pesan karena ini adalah interaksi non-deferred
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.send_message("Ini sudah halaman terakhir, klik **Refresh** untuk mendapatkan server baru.", ephemeral=True)

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.success, custom_id="refresh_button")
    async def refresh(self, interaction: discord.Interaction, button):
        """Tombol untuk mengambil ulang data server."""
        # Defer the interaction response. This shows the 'Loading...' state.
        await interaction.response.defer()
        
        # Ambil data server baru
        new_servers = await self.refresh_servers()
        
        if not new_servers:
            # Kirim pesan error private jika gagal refresh
            return await interaction.followup.send("⚠️ Gagal refresh data.", ephemeral=True)

        # Perbarui data dan reset halaman
        self.servers = new_servers
        self.page = 0 

        # FIX: Gunakan interaction.message.edit untuk memperbarui konten pesan
        await interaction.message.edit(embed=self.get_embed(), view=self)

# --- Command Bot ---
@bot.command()
async def roblox(ctx):
    """Command /roblox untuk menampilkan daftar server publik."""
    
    # 1. Kirim pesan 'loading' dan simpan referensinya
    loading_message = await ctx.send("🔍 Mengambil data server...")

    # 2. Ambil data server
    servers = await fetch_roblox_servers(limit=10) 

    # 3. Periksa kegagalan data
    if not servers:
        # Edit pesan loading menjadi pesan error
        return await loading_message.edit(content="❌ Tidak bisa mengambil data server Roblox atau tidak ada server ditemukan.")

    # 4. Inisialisasi Paginator dan kirim hasilnya
    view = ServerPaginator(servers)
    # Edit pesan loading menjadi embed dan view interaktif
    await loading_message.edit(content=None, embed=view.get_embed(), view=view)

bot.run(os.environ.get("DISCORD_TOKEN"))
