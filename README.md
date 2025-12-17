# 🎤 TYSA: The Yapping Spotify Announcer

![TYSA Logo](tysa.jpg)

TYSA is your digital radio DJ. A Python script that detects your current Spotify track and announces it with smooth, AI-generated commentary. It's like having a late-night FM host living in your terminal.

Yes, I know this completely outs me as someone who listens to classical music. And yes, that's exactly why GPT simplification exists - because nobody wants to hear "Symphony No. 9 in D Minor, Op. 125 'Choral': IV. Presto - Allegro assai" when you can just say "Ode to Joy." 🎻

## 🎙️ The Origin Story

Spotify Wrapped told me I'm in the top 1% of listeners with 100,000 minutes streamed. Impressive, right? Plot twist: play me my top song and I can barely tell you the name or artist. Turns out you can listen to thousands of hours of music and learn absolutely nothing if you're not paying attention.

So I figured, what if I learned unconsciously? If someone announced the song and artist every single time a track played, maybe, just maybe - the information would eventually stick. TYSA is that someone. Now my terminal is a radio DJ that won't shut up, and honestly, it's working.

## Features

- GPT-4o-mini simplifies complex classical titles
- ElevenLabs TTS for natural voice announcements
- Caches everything—replays cost $0
- Uses AppleScript (no Spotify OAuth needed)
- Polls every second for instant detection

## Setup

```bash
git clone <your-repo-url>
cd tysa
cp .env.example .env
```

Add your API keys to `.env`:
- ElevenLabs: https://elevenlabs.io/
- OpenAI (optional): https://platform.openai.com/api-keys

Run it:
```bash
./run.sh
```

Stop with `Ctrl+C` or `pkill -f tysa.py`

## Configuration

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

## How It Works

1. AppleScript polls Spotify for track changes
2. GPT simplifies titles (strips opus numbers, movements, key signatures)
3. ElevenLabs generates the announcement
4. Audio plays via `afplay`
5. Everything caches for next time

Generated files go to `output/` like `Beethoven_Moonlight_Sonata.mp3`

## Troubleshooting

**"Nothing is currently playing"** - Spotify must be running and playing

**"Missing required environment variables"** - Check `.env` has `ELEVENLABS_API_KEY`

**Permission errors** - System Preferences → Privacy & Security → Automation, grant terminal access to Spotify

**Volume issues** - Adjust `PLAYBACK_VOLUME` in `.env` (0.0 to 1.0)

## Advanced

Run once:
```bash
RUN_MODE=once ./run.sh
```

Manual Python:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python tysa.py
```

## Requirements

macOS, Python 3.8+, Spotify Desktop, ElevenLabs API key, OpenAI API key (optional)

## License

MIT
