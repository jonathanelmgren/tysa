# 🎤 TYSA: The Yapping Spotify Announcer

![TYSA Logo](tysa.jpg)

TYSA is your digital radio DJ. A Python script that detects your current Spotify track and announces it with smooth, AI-generated commentary. It's like having a late-night FM host living in your terminal.

Yes, I know this completely outs me as someone who listens to classical music. And yes, that's exactly why GPT simplification exists - because nobody wants to hear "Symphony No. 9 in D Minor, Op. 125 'Choral': IV. Presto - Allegro assai" when you can just say "Ode to Joy." 🎻

## ✨ What's in The Booth

**Smart Yapping:** Simplifies complex classical titles using GPT-4o-mini so your announcements sound natural instead of reading a library catalog.

**Radio Voice:** Uses ElevenLabs TTS with the "Eric" voice for that broadcast feel. Set the volume anywhere from 0.0 (silent) to 1.0 (max).

**Caching:** Never pays twice. Caches both GPT responses and audio files so replaying a track costs exactly $0.

**Instant Detection:** Polls every second to catch track changes fast. No more dead air between songs.

**macOS Native:** Uses AppleScript, which means no OAuth nightmares with Spotify's Web API. It just works.

**Silent Mode:** Logs to file only unless you set DEBUG=true. Keep the booth clean.

## 🚀 Quick Start (Spinning Up)

### Installation

Clone the repo and copy the env file:

```bash
git clone <your-repo-url>
cd tysa
cp .env.example .env
```

Add your API keys to `.env`:
- ElevenLabs API key (required): https://elevenlabs.io/
- OpenAI API key (optional): https://platform.openai.com/api-keys

### Run It

```bash
./run.sh
```

That's it! TYSA will set up a virtual environment on first run, install dependencies automatically, and start yapping whenever you change tracks.

**To stop:** Press `Ctrl+C` or kill the process with `pkill -f tysa.py` (or run in background with something like pm2, tmux or screen).

## ⚙️ Configuration (Tuning The Booth)

All settings live in your `.env` file:

| Variable | Default | What It Does |
|----------|---------|--------------|
| `ELEVENLABS_API_KEY` | *required* | Your ElevenLabs API key |
| `ELEVENLABS_VOICE_ID` | `cjVigY5qzO86Huf0OWal` | Voice ID (default: Eric) |
| `OPENAI_API_KEY` | *optional* | Only needed if GPT simplification is on |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for title simplification |
| `PLAYBACK_VOLUME` | `0.5` | Volume (0.0=silent, 1.0=max) |
| `POLL_INTERVAL_SECONDS` | `1` | How often to check for track changes |
| `ENABLE_GPT_SIMPLIFICATION` | `true` | Simplify classical titles? |
| `DEBUG` | `false` | Log to terminal (true) or file only (false) |
| `OUTPUT_DIR` | `output` | Where to save generated MP3s |
| `RUN_MODE` | `continuous` | `continuous` or `once` |

### Example: Quiet Mode
```bash
PLAYBACK_VOLUME=0.3 ./run.sh
```

### Example: Yell Mode
```bash
PLAYBACK_VOLUME=1.0 ./run.sh
```

## 🎙️ How The Yapping Works

**Step 1:** AppleScript checks Spotify every second for track changes.

**Step 2:** If GPT simplification is enabled, it strips out opus numbers, movements, and key signatures.

**Step 3:** ElevenLabs generates a natural announcement with the Eric voice.

**Step 4:** TYSA plays the audio using macOS's `afplay` command.

**Step 5:** Both the GPT result and audio file are saved for next time.

### What You'll Hear

Instead of this nightmare:
> "Symphony No. 9 in D Minor, Op. 125 'Choral': IV. Presto - Allegro assai by Ludwig van Beethoven"

You get this:
> **"Now playing: Ode to Joy - by Beethoven"** 🎵

## 📂 Output & Caching

Generated announcements are saved to `output/` with clean filenames:

```
output/
├── Beethoven_Moonlight_Sonata.mp3
├── Offenbach_Cancan.mp3
└── Mussorgsky_Night_on_Bald_Mountain.mp3
```

### The Caching System

**GPT Cache** (`.gpt_cache.json`) stores simplified titles so you never call ChatGPT twice for the same track.

**Audio Cache** (`output/` directory) reuses MP3 files so you never call ElevenLabs twice for the same announcement.

**Translation:** Once a track is announced, it's cached forever. Replays cost $0. 💰

## 🎚️ Advanced Usage

### Single-Shot Mode

Announce the current track once and exit:
```bash
RUN_MODE=once ./run.sh
```

### Manual Python Usage

If you want full control:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python tysa.py
```

### Kill All TYSA Processes

```bash
pkill -f tysa.py
```

## 🐛 Troubleshooting (Dead Air Prevention)

### "Nothing is currently playing"
Make sure Spotify is running and a track is playing (not paused).

### "Missing required environment variables"
Check that your `.env` file exists. `ELEVENLABS_API_KEY` is always required. `OPENAI_API_KEY` is only needed if `ENABLE_GPT_SIMPLIFICATION=true`.

### Permission errors with AppleScript
Go to **System Preferences → Privacy & Security → Automation** and grant your terminal app permission to control Spotify.

### Volume is too loud/quiet
Adjust `PLAYBACK_VOLUME` in `.env` (range: 0.0 to 1.0). Default is 0.5 (50%).

## 🎵 Title Simplification (The Classical Problem)

When enabled, GPT strips out all the unnecessary metadata from classical music titles.

**What gets removed:** Opus numbers (Op. 71, Op.posth), movement numbers (I., II., III.), tempo markings (Allegro, Andante, Presto), catalog numbers (BWV 565, K. 331, D. 960), key signatures (in E Major, in D Minor), and remaster notes (2023 Remaster, Radio Edit).

**What stays:** The main piece name and recognizable subtitles like "Ode to Joy."

**Composer shortening:** Pyotr Ilyich Tchaikovsky becomes Tchaikovsky. Ludwig van Beethoven becomes Beethoven. Wolfgang Amadeus Mozart becomes Mozart.

**To disable:** Set `ENABLE_GPT_SIMPLIFICATION=false` in `.env`

## 📜 The TYSA Dictionary

**Yap (v.):** To announce a song. *"TYSA starts yapping when the track changes."*

**The Booth:** The terminal where the script is running.

**Spinning:** Playing a track.

**Dead Air:** When the script crashes (we avoid this).

**Silence:** The enemy.

## 📦 Requirements

You'll need **macOS** (uses AppleScript, sorry Windows/Linux folks), **Python 3.8+**, **Spotify Desktop App** (must be running), **ElevenLabs API Key** (required), and **OpenAI API Key** (optional, for title simplification).

## 📝 License

MIT

## 💡 Notes

This is a personal project vibe coded for macOS with Claude Code. The AppleScript approach means no OAuth nightmares with Spotify's Web API—it just works.

**Made with ❤️ and way too much classical music.**

## 🎧 Pro Tips

Set `POLL_INTERVAL_SECONDS=1` for instant announcements. Use `DEBUG=true` if you want to see logs in the terminal. Lower `PLAYBACK_VOLUME` if TYSA is too hype. Disable GPT simplification if you actually like reading opus numbers.

**Keep it locked. TYSA out.** 📻
