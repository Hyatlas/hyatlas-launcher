# Hyatlas Launcher

**Hyatlas** was born after the unfortunate news that *Hytale* will never see the light of day.  
We were truly excited for it—so we decided to carry that dream forward in an **open-source** project the whole community can shape.

---

## 🚀 Why a dedicated launcher?

- **One-Click Play** – The launcher always grabs the exact client build required by any server, official or self-hosted.  
- **Auto-Updates** – Signed monthly updates roll out automatically; self-hosted servers receive them with zero manual work.  
- **Mod & Asset Management** – Mods, plugins, and official cosmetic packs install on the fly when you join a server.

---

## 📚 Hyatlas repository overview

| Repository | Purpose |
|------------|---------|
| **[hyatlas-game](https://github.com/Hyatlas/hyatlas-game)** | Unity project (client + server); core gameplay and engine |
| **hyatlas-launcher** *(this repo)* | Bootstrap installer, auto-patcher, update logic |
| **[hyatlas-modkit](https://github.com/Hyatlas/hyatlas-modkit)** | SDK & APIs for building mods and plugins |
| **[hyatlas-mod-examples](https://github.com/Hyatlas/hyatlas-mod-examples)** | Sample mods, smoke tests, CI templates |
| **[hyatlas-server-toolkit](https://github.com/Hyatlas/hyatlas-server-toolkit)** | CLI to package, sign, and publish self-hosted servers |
| **[hyatlas-docs](https://github.com/Hyatlas/hyatlas-docs)** | Documentation, contributor guide, design docs |

*(Private repos for premium assets, the marketplace backend, and DevOps infrastructure are not listed here.)*

---

## 🤝 Contribute!

- **Anyone** can open issues, submit pull requests, or brainstorm ideas on Discord.  
- The **game is always playable** – our CI/CD pipeline publishes fresh nightlies after every merge.  
- **Self-hosted servers** receive stable updates automatically on a monthly cadence.

---

## 🆓 Forever open-source & free to play

Hyatlas will **always** remain open source **and** free for players.  
The code is licensed under **Hyatlas Open Source License 1.0** (AGPL-v3 + Non-Commercial clause).  
See the `LICENSE` file for details.

---

## 💎 Monetization & marketplace rules

To fund better features, content drops, and server costs:

1. **Cosmetic items** (skins, emotes, pets) may be sold **only** through the official **Hyatlas Marketplace**.  
2. **Paid mods & plugins** must also go through the marketplace.  
3. Third-party shop operators can request exceptions; a **small per-sale fee** applies.  
4. The exact model is a work in progress – **community feedback is welcome!**

Everything else (core code, free mods, resource packs) stays completely free.

---

## 🌄 Vision – What kind of game is Hyatlas?

> *“Imagine a living voxel world blending Minecraft-style creativity with Hytale’s adventure flair and stylized visuals.”*

- **Voxel sandbox** with fully destructible terrain, crafting, and building  
- **Procedural continents**: mountains, caves, oceans, diverse biomes  
- **RPG layer**: quests, dungeons, boss fights, talent trees  
- **Modding-first**: every block, item, and quest can be extended via the modkit  
- **Server-centric**: from tiny LAN worlds to global MMO shards – everything is possible  
- **Community-driven roadmap**: transparent polls, open pull requests

If that vision excites you, dive into the code, start tinkering, and help make **Hyatlas** a reality!

---

### 📥 Developer quick-start

```bash
git clone https://github.com/Hyatlas/hyatlas-launcher.git
cd hyatlas-launcher
dotnet run
# The launcher starts, fetches the latest nightly, and launches the game
```

### 💬 Need help?

• Chat & support: discord.gg/hyatlas
• Roadmap & tasks: see GitHub Projects in each repo


Thanks for stopping by – we can’t wait to see your contributions!
– The Hyatlas Team
