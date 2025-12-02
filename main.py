import discord
from discord.ext import commands
import aiohttp
import os
import asyncio # Diperlukan untuk penanganan asinkron yang lebih baik

# Konfigurasi Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Place ID Roblox yang digunakan (Fish-it)
ROBLOX_PLACE_ID = 121864768012064

@bot.event
async def on_ready():
    print(f"Bot online sebagai {bot.user}")


class ServerPaginator(discord.ui.View):
    def __init__(self, servers):
        super().__init__(timeout=60)

        self.servers = servers
        self.page = 0

        # Join button (link updated dynamically)
        self.join_button = discord.ui.Button(
            label="🔗 Join",
            style=discord.ButtonStyle.link,
            url="https://roblox.com"
        )
        self.add_item(self.join_button)

    async def refresh_servers(self):
        url = "https://games.roblox.com/v1/games/121864768012064/servers/Public?limit=100&sortOrder=Desc&excludeFullGames=true"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return None
                    data = await resp.json()
                    return data.get("data", [])[:10]
            except:
                return None

    def get_embed(self):
        server = self.servers[self.page]
        server_id = server.get("id", "Unknown")
        playing = server.get("playing", 0)
        maxPlayers = server.get("maxPlayers", 0)
        ping = server.get("ping") or "Unavailable"
        fps = server.get("fps") or "Unavailable"

        # update join button URL
        self.join_button.url = f"https://www.roblox.com/games/start?placeId=121864768012064&serverId={server_id}"

        embed = discord.Embed(
            title=f"🎣 Server Public Fish-it ({self.page+1}/{len(self.servers)})",
            color=0x57F287
        )
        embed.add_field(name="Server ID", value=server_id, inline=False)
        embed.add_field(name="Players", value=f"{playing}/{maxPlayers}", inline=True)
        embed.add_field(name="Ping", value=f"{ping}", inline=True)
        embed.add_field(name="FPS", value=f"{fps}", inline=True)

        return embed

    @discord.ui.button(label="⬅ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction, button):
        if self.page > 0:
            self.page -= 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Next ➡", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        if self.page < len(self.servers) - 1:
            self.page += 1
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

@discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.success)
    async def refresh(self, interaction: discord.Interaction, button):
        # Defer the interaction response. This shows the 'Loading...' state.
        await interaction.response.defer()
        
        # Call the method to fetch new server data
        new_servers = await self.refresh_servers()
        
        # Check if the data fetch failed
        if not new_servers:
            # Send a private error message (ephemeral=True) if data failed to refresh
            return await interaction.followup.send("⚠️ Gagal refresh data.", ephemeral=True)

        # Update the view's data
        self.servers = new_servers
        self.page = 0  # Reset to the first page

        # FIX: Use interaction.message.edit to update the content of the message
        # where the view is attached.
        await interaction.message.edit(embed=self.get_embed(), view=self)


@bot.command()
async def roblox(ctx):
    await ctx.send("🔍 Mengambil data server...")

    url = "https://games.roblox.com/v1/games/121864768012064/servers/Public?limit=10&sortOrder=Desc&excludeFullGames=true"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return await ctx.send("❌ Tidak bisa mengambil data server Roblox.")
            data = await resp.json()

    servers = data.get("data", [])
    if not servers:
        return await ctx.send("❌ Tidak ada server ditemukan.")

    servers = servers[:10]

    view = ServerPaginator(servers)
    await ctx.send(embed=view.get_embed(), view=view)

bot.run(os.environ.get("DISCORD_TOKEN"))
