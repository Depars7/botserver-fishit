const { Client, GatewayIntentBits, EmbedBuilder, ButtonBuilder, ButtonStyle, ActionRowBuilder, Events } = require("discord.js");
const fetch = require("node-fetch");

const client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent]
});

client.on("error", (err) => {
  console.log("Bot Error:", err);
});

client.on("shardError", (error) => {
  console.error("A websocket connection ERROR occurred:", error);
});

process.on("unhandledRejection", (reason, promise) => {
  console.log("[Unhandled Rejection]:", reason);
});

// Fetch server list function
async function getServers(limit = 10) {
    const url = `https://games.roblox.com/v1/games/121864768012064/servers/Public?limit=100&sortOrder=Desc&excludeFullGames=true`;
    
    try {
        const res = await fetch(url);
        if (!res.ok) return null;
        const json = await res.json();
        return json.data.slice(0, limit);
    } catch {
        return null;
    }
}

client.once(Events.ClientReady, () => {
    console.log(`Bot online sebagai ${client.user.tag}`);
});

async function buildEmbed(servers, page) {
    const server = servers[page];
    const serverId = server.id;
    const playing = server.playing || 0;
    const maxPlayers = server.maxPlayers || 0;
    const ping = server.ping ?? "Unavailable";
    const fps = server.fps ?? "Unavailable";

    return new EmbedBuilder()
        .setTitle(`🎣 Server Public Fish-it (${page + 1}/${servers.length})`)
        .setColor(0x57F287)
        .addFields(
            { name: "Server ID", value: serverId.toString(), inline: false },
            { name: "Players", value: `${playing}/${maxPlayers}`, inline: true },
            { name: "Ping", value: `${ping}`, inline: true },
            { name: "FPS", value: `${fps}`, inline: true }
        );
}

client.on("messageCreate", async (message) => {
    if (message.content.toLowerCase() === "/roblox") {
        await message.reply("🔍 Mengambil data server...");

        const servers = await getServers();
        if (!servers || servers.length === 0)
            return message.channel.send("❌ Tidak ada server ditemukan.");

        let page = 0;

        const embed = await buildEmbed(servers, page);

        // Buttons
        let row = new ActionRowBuilder().addComponents(
            new ButtonBuilder()
                .setCustomId("prev")
                .setLabel("⬅ Prev")
                .setStyle(ButtonStyle.Secondary),

            new ButtonBuilder()
                .setCustomId("next")
                .setLabel("Next ➡")
                .setStyle(ButtonStyle.Secondary),

            new ButtonBuilder()
                .setCustomId("refresh")
                .setLabel("🔄 Refresh")
                .setStyle(ButtonStyle.Success),

            new ButtonBuilder()
                .setLabel("🔗 Join")
                .setStyle(ButtonStyle.Link)
                .setURL(`https://www.roblox.com/games/start?placeId=121864768012064&serverId=${servers[page].id}`)
        );

        const msg = await message.channel.send({ embeds: [embed], components: [row] });

        const filter = (interaction) =>
            interaction.isButton() && interaction.message.id === msg.id;

        const collector = message.channel.createMessageComponentCollector({
            filter,
            time: 60000,
        });

        collector.on("collect", async (interaction) => {
            if (!servers) return;

            if (interaction.customId === "prev") {
                if (page > 0) page--;
            }

            if (interaction.customId === "next") {
                if (page < servers.length - 1) page++;
            }

            if (interaction.customId === "refresh") {
                const newServers = await getServers();
                if (newServers) {
                    servers.length = 0;
                    newServers.forEach((s) => servers.push(s));
                    page = 0;
                } else {
                    return interaction.reply({ content: "⚠️ Gagal refresh data.", ephemeral: true });
                }
            }

            // Update embed and buttons
            const newEmbed = await buildEmbed(servers, page);

            const newRow = new ActionRowBuilder().addComponents(
                new ButtonBuilder()
                    .setCustomId("prev")
                    .setLabel("⬅ Prev")
                    .setStyle(ButtonStyle.Secondary),

                new ButtonBuilder()
                    .setCustomId("next")
                    .setLabel("Next ➡")
                    .setStyle(ButtonStyle.Secondary),

                new ButtonBuilder()
                    .setCustomId("refresh")
                    .setLabel("🔄 Refresh")
                    .setStyle(ButtonStyle.Success),

                new ButtonBuilder()
                    .setLabel("🔗 Join")
                    .setStyle(ButtonStyle.Link)
                    .setURL(`https://www.roblox.com/games/start?placeId=121864768012064&serverId=${servers[page].id}`)
            );

            await interaction.update({ embeds: [newEmbed], components: [newRow] });
        });
    }
});

client.login(process.env.DISCORD_TOKEN);
