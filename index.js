const { 
  Client, 
  GatewayIntentBits, 
  Partials, 
  EmbedBuilder, 
  ButtonBuilder, 
  ButtonStyle, 
  ActionRowBuilder,
  // Kita tambahkan REST dan Routes untuk registrasi commands, meskipun lebih baik di file terpisah
  REST, 
  Routes
} = require("discord.js");
require("./server.js"); // Untuk keep-alive di platform hosting

const fetch = require("node-fetch");
require("dotenv").config(); // Di Koyeb, ini hanya diperlukan untuk testing lokal

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent
  ],
  partials: [Partials.Channel]
});

// ID Game Roblox Fish-it: 121864768012064
const PLACE_ID = "121864768012064";

/**
 * Mengambil daftar server Roblox
 * @param {number} limit - Jumlah server yang diinginkan
 * @returns {Array<Object> | null} Daftar server atau null jika gagal
 */
async function getServers(limit = 10) {
  try {
    const res = await fetch(`https://games.roblox.com/v1/games/${PLACE_ID}/servers/Public?limit=${limit}&excludeFullGames=true`);
    
    if (!res.ok) {
      console.error(`Roblox API returned status: ${res.status}`);
      return null;
    }

    const json = await res.json();
    return json.data.slice(0, limit);
  } catch (error) {
    console.error("Error saat fetch Roblox API:", error.message);
    return null;
  }
}

/**
 * Membangun Embed untuk menampilkan data server
 * @param {Array<Object>} servers - Daftar server
 * @param {number} page - Index halaman saat ini
 * @returns {EmbedBuilder}
 */
function buildEmbed(servers, page) {
  const s = servers[page];

  // Cek apakah server valid
  if (!s) {
    return new EmbedBuilder()
      .setTitle("❌ Server Tidak Ditemukan")
      .setDescription("Server ini mungkin telah ditutup atau data tidak tersedia.")
      .setColor(0xEE4B2B);
  }

  return new EmbedBuilder()
    .setTitle(`🎣 Server Public Fish-it (${page + 1}/${servers.length})`)
    .setColor(0x57F287)
    .addFields(
      { name: "Server ID", value: s.id.toString(), inline: false },
      { name: "Players", value: `${s.playing}/${s.maxPlayers}`, inline: true },
      { name: "Ping", value: `${s.ping ?? "N/A"}`, inline: true },
      { name: "FPS", value: `${s.fps ?? "N/A"}`, inline: true }
    )
    .setFooter({ text: `Update terakhir: ${new Date().toLocaleTimeString('id-ID')}` });
}

/**
 * Membuat ActionRow dengan tombol navigasi, refresh, dan join
 * @param {Array<Object>} servers - Daftar server
 * @param {number} page - Index halaman saat ini
 * @returns {ActionRowBuilder}
 */
const makeRow = (servers, page) => {
    // Tombol PREV dinonaktifkan jika di halaman 0
    const prevButton = new ButtonBuilder()
        .setCustomId("prev")
        .setLabel("⬅ Prev")
        .setStyle(ButtonStyle.Secondary)
        .setDisabled(page === 0);

    // Tombol NEXT dinonaktifkan jika di halaman terakhir
    const nextButton = new ButtonBuilder()
        .setCustomId("next")
        .setLabel("Next ➡")
        .setStyle(ButtonStyle.Secondary)
        .setDisabled(page === servers.length - 1);

    const refreshButton = new ButtonBuilder()
        .setCustomId("refresh")
        .setLabel("🔄 Refresh")
        .setStyle(ButtonStyle.Success);

    // Tombol JOIN (URL akan berubah sesuai server ID saat ini)
    const joinUrl = `https://www.roblox.com/games/start?placeId=${PLACE_ID}&serverId=${servers[page].id}`;
    const joinButton = new ButtonBuilder()
        .setLabel("🔗 Join")
        .setURL(joinUrl)
        .setStyle(ButtonStyle.Link);
    
    return new ActionRowBuilder().addComponents(
        prevButton,
        nextButton,
        refreshButton,
        joinButton
    );
};

// --- CLIENT EVENTS ---

// Event Bot siap (Mengganti 'ready' menjadi 'clientReady' untuk menghindari Deprecation Warning)
client.on("clientReady", () => {
  console.log("Bot online:", client.user.tag);
  // Opsional: Daftarkan slash command di sini jika kamu tidak menggunakan file deploy terpisah
  // registerCommands(); 
});


// Slash Command Handler
client.on("interactionCreate", async interaction => {
  if (!interaction.isChatInputCommand()) return;

  if (interaction.commandName === "getserver") {

    // 1. Tanggapi interaksi segera untuk menghindari timeout
    await interaction.deferReply(); 

    let servers = await getServers();
    if (!servers || servers.length === 0) {
      return interaction.editReply("❌ Tidak ada server ditemukan atau API gagal.");
    }

    let page = 0;

    const embed = buildEmbed(servers, page);
    const row = makeRow(servers, page);

    const msg = await interaction.editReply({ embeds: [embed], components: [row] });

    // Membuat kolektor untuk tombol, timeout 60 detik
    const collector = msg.createMessageComponentCollector({ time: 60000 });

    collector.on("collect", async btn => {
      // Hanya izinkan pengguna yang memanggil command untuk berinteraksi
      if (btn.user.id !== interaction.user.id) {
        return btn.reply({ content: "Ini bukan interaksi kamu!", ephemeral: true });
      }

      // Defer update agar Discord tahu kita sedang memproses
      await btn.deferUpdate(); 
      
      let shouldUpdate = false;

      // Logika Navigasi
      if (btn.customId === "prev" && page > 0) {
        page--;
        shouldUpdate = true;
      } else if (btn.customId === "next" && page < servers.length - 1) {
        page++;
        shouldUpdate = true;
      }

      // Logika Refresh
      if (btn.customId === "refresh") {
        await btn.editReply({ content: "🔄 Mengambil data server terbaru...", ephemeral: true }); // Tampilkan pesan loading
        
        const newServers = await getServers();
        
        if (!newServers) {
          return btn.editReply({ content: "⚠️ Refresh gagal", ephemeral: true });
        }
        
        servers = newServers;
        page = 0; // Reset ke halaman pertama setelah refresh
        shouldUpdate = true;
      }

      // Kirim pembaruan pesan jika ada perubahan
      if (shouldUpdate) {
        await msg.edit({
          embeds: [buildEmbed(servers, page)], 
          components: [makeRow(servers, page)] 
        });
      }
    });

    collector.on("end", async () => {
      // Nonaktifkan semua tombol setelah collector timeout
      const disabledRow = makeRow(servers, page);
      disabledRow.components.forEach(b => b.setDisabled(true));

      await msg.edit({ components: [disabledRow] }).catch(()=>{});
    });
  }
});


client.login(process.env.DISCORD_TOKEN);


// --- FUNGSI REGISTRASI COMMAND (OPSIONAL, HANYA UNTUK KEPERLUAN DEMO) ---
// Biasanya ini dilakukan sekali saja, atau saat bot dimulai.
async function registerCommands() {
    // Pastikan CLIENT_ID dan GUILD_ID ada di .env jika menggunakan Global/Guild Command
    if (!process.env.CLIENT_ID || !process.env.DISCORD_TOKEN) {
        console.error("Missing CLIENT_ID or DISCORD_TOKEN for command registration.");
        return;
    }

    const commands = [
        {
            name: "getserver",
            description: "Menampilkan daftar server publik Fish-it yang tidak penuh."
        }
    ];

    const rest = new REST({ version: "10" }).setToken(process.env.DISCORD_TOKEN);

    try {
        console.log("Mulai refresh (/) commands.");

        // Jika kamu ingin mendaftarkan di GUILD tertentu (lebih cepat untuk testing):
        if (process.env.GUILD_ID) {
             await rest.put(
                Routes.applicationGuildCommands(process.env.CLIENT_ID, process.env.GUILD_ID),
                { body: commands },
            );
            console.log("Berhasil merefresh GUILD (/) commands.");
        } else {
            // Jika ingin mendaftarkan secara Global (memakan waktu ~1 jam):
            await rest.put(
                Routes.applicationCommands(process.env.CLIENT_ID),
                { body: commands },
            );
            console.log("Berhasil merefresh GLOBAL (/) commands.");
        }
    } catch (error) {
        console.error("Gagal mendaftarkan commands:", error);
    }
}
