# TYSA - The Yapping Spotify Announcer

A production-grade Python script that monitors your Spotify playback, simplifies track titles using GPT, and generates spoken announcements with ElevenLabs text-to-speech.

## Features

- Automatically detects currently playing Spotify tracks (macOS only via AppleScript)
- Uses GPT to simplify complex song titles (removes opus numbers, movement markings, etc.)
- Generates natural-sounding speech announcements with ElevenLabs
- Continuous monitoring mode with configurable polling intervals
- Comprehensive logging and error handling
- Environment variable configuration

## Requirements

- macOS (uses AppleScript to communicate with Spotify)
- Python 3.8+
- Spotify desktop app
- OpenAI API key
- ElevenLabs API key

## Installation

1. Clone or download this repository

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Copy the example environment file:
```bash
cp .env.example .env
```

4. Edit `.env` and add your API keys:
```bash
# Get OpenAI API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=your_openai_api_key_here

# Get ElevenLabs API key from: https://elevenlabs.io/
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Optional: Choose a different voice from https://elevenlabs.io/voice-library
ELEVENLABS_VOICE_ID=EXAVITQu4vr4xnSDxMaL
```

## Usage

### Continuous Mode (Default)

Run the script to continuously monitor Spotify and announce new tracks:

```bash
python tysa.py
```

The script will:
- Poll Spotify every 5 seconds (configurable)
- Detect when a new track starts playing
- Generate and save an announcement audio file
- Continue running until you press Ctrl+C

### Single-Shot Mode

Process only the currently playing track and exit:

```bash
RUN_MODE=once python tysa.py
```

## Configuration

All configuration is done via the `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *required* | Your OpenAI API key |
| `ELEVENLABS_API_KEY` | *required* | Your ElevenLabs API key |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI model for title simplification |
| `ELEVENLABS_VOICE_ID` | `EXAVITQu4vr4xnSDxMaL` | ElevenLabs voice ID (Sarah) |
| `OUTPUT_DIR` | `output` | Directory for generated audio files |
| `POLL_INTERVAL_SECONDS` | `5` | How often to check for track changes |
| `RUN_MODE` | `continuous` | Run mode: `continuous` or `once` |

## Output

Generated announcements are saved to the `output/` directory with filenames like:
```
announcement_20231215_143022.mp3
```

Each file contains a spoken announcement like:
> "Now playing: Moonlight Sonata by Beethoven"

## Logging

Logs are written to both:
- Console (stdout)
- `tysa.log` file

Log levels can be adjusted in the script if needed.

## Title Simplification

The GPT integration automatically simplifies complex classical music titles by removing:
- Opus numbers (Op. 71, Op.posth)
- Movement numbers (I., II., III.)
- Tempo markings (Allegro, Andante, etc.)
- Catalog numbers (BWV 565, K. 331, etc.)
- Key signatures (in E Major, etc.)
- Remaster notes and version info

Composer names are also shortened (e.g., "Pyotr Ilyich Tchaikovsky" → "Tchaikovsky")

## Troubleshooting

### "Nothing is currently playing"
- Make sure Spotify desktop app is running
- Make sure a track is actually playing (not paused)

### "Missing required environment variables"
- Check that your `.env` file exists
- Verify both `OPENAI_API_KEY` and `ELEVENLABS_API_KEY` are set

### Permission errors with AppleScript
- Grant Terminal/your terminal app permission to control Spotify in System Preferences → Privacy & Security → Automation

## License

MIT

## Notes

This is a personal project designed for macOS. The AppleScript integration means it won't work on Windows or Linux, but it's much simpler than using Spotify's Web API!
