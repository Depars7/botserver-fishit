const { 
    Client, 
    GatewayIntentBits, 
    Partials, 
    EmbedBuilder, 
    ButtonBuilder, 
    ButtonStyle, 
    ActionRowBuilder 
} = require("discord.js");

const fetch = require("node-fetch");
require("dotenv").config();

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent
    ],
    partials: [Partials.Channel]
});

// fetch roblox server
async function getServers(limit = 10) {
    try {
        const res = await fetch(`https://games.roblox.com/v1/games/121864768012064/servers/Public?limit=100&excludeFullGames=true`);
        if (!res.ok) return null;

        const json = await res.json();
        return json.data.slice(0, limit);
    } catch {
        return null;
    }
}

function buildEmbed(servers, page) {
    const s = servers[page];

    return new EmbedBuilder()
        .setTitle(`🎣 Server Public Fish-it (${page + 1}/${servers.length})`)
        .setColor(0x57F287)
        .addFields(
            { name: "Server ID", value: s.id.toString(), inline: false },
            { name: "Players", value: `${s.playing}/${s.maxPlayers}`, inline: true },
            { name: "Ping", value: `${s.ping ?? "N/A"}`, inline: true },
            { name: "FPS", value: `${s.fps ?? "N/A"}`, inline: true }
        );
}

client.on("ready", () => {
    console.log("Bot online:", client.user.tag);
});

// Slash Command Handler
client.on("interactionCreate", async interaction => {
    if (!interaction.isChatInputCommand()) return;

    if (interaction.commandName === "getserver") {
        
        await interaction.reply("🔍 Fetching server list...");

        let servers = await getServers();
        if (!servers || servers.length === 0) 
            return interaction.editReply("❌ Tidak ada server ditemukan.");

        let page = 0;

        const embed = buildEmbed(servers, page);

        const makeRow = () =>
            new ActionRowBuilder().addComponents(
                new ButtonBuilder().setCustomId("prev").setLabel("⬅ Prev").setStyle(ButtonStyle.Secondary),
                new ButtonBuilder().setCustomId("next").setLabel("Next ➡").setStyle(ButtonStyle.Secondary),
                new ButtonBuilder().setCustomId("refresh").setLabel("🔄 Refresh").setStyle(ButtonStyle.Success),
                new ButtonBuilder()
                    .setLabel("🔗 Join")
                    .setURL(`https://www.roblox.com/games/start?placeId=121864768012064&serverId=${servers[page].id}`)
                    .setStyle(ButtonStyle.Link)
            );

        const msg = await interaction.editReply({ embeds: [embed], components: [makeRow()] });

        const collector = msg.createMessageComponentCollector({ time: 60000 });

        collector.on("collect", async btn => {
            
            if (btn.customId === "prev" && page > 0) page--;
            if (btn.customId === "next" && page < servers.length - 1) page++;

            if (btn.customId === "refresh") {
                const newServers = await getServers();
                if (!newServers)
                    return btn.reply({ content: "⚠️ Refresh failed", ephemeral: true });

                servers = newServers;
                page = 0;
            }

            await btn.update({ 
                embeds: [buildEmbed(servers, page)], 
                components: [makeRow()] 
            });
        });

        collector.on("end", async () => {
            const disabledRow = new ActionRowBuilder().addComponents(
                makeRow().components.map(b => ButtonBuilder.from(b).setDisabled(true))
            );

            await msg.edit({ components: [disabledRow] }).catch(()=>{});
        });
    }
});

client.login(process.env.DISCORD_TOKEN);