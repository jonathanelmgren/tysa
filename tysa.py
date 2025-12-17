#!/usr/bin/env python3
"""
TYSA - The Yapping Spotify Announcer
Gets currently playing Spotify track, simplifies the title with GPT, and generates TTS with ElevenLabs.
"""

import os
import sys
import time
import logging
import subprocess
import re
import json
from typing import Optional, Tuple, Dict

from openai import OpenAI
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

load_dotenv()

handlers: list[logging.Handler] = [logging.FileHandler('tysa.log')]
if os.getenv('DEBUG', 'false').lower() == 'true':
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)


class SpotifyAnnouncer:
    """Main class for TYSA - The Yapping Spotify Announcer"""

    def __init__(self):
        """Initialize the announcer with API clients"""
        load_dotenv()
        self._validate_env_vars()

        self.mode = os.getenv('MODE', 'smart').lower()
        if self.mode not in ['basic', 'smart', 'wizard']:
            logger.warning(f"Invalid MODE '{self.mode}', defaulting to 'smart'")
            self.mode = 'smart'

        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'RexqLjNzkCjWogguKyff')
        self.language_code = os.getenv('LANGUAGE_CODE', 'en')
        self.now_playing_text = os.getenv('NOW_PLAYING_TEXT', 'Now playing')
        self.by_text = os.getenv('BY_TEXT', 'by')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.output_dir = os.getenv('OUTPUT_DIR', 'output')
        self.poll_interval = int(os.getenv('POLL_INTERVAL_SECONDS', '1'))
        self.gpt_cache_file = os.getenv('GPT_CACHE_FILE', '.gpt_cache.json')
        self.volume = float(os.getenv('PLAYBACK_VOLUME', '0.5'))

        # OpenAI only required for smart/wizard modes
        if self.mode in ['smart', 'wizard']:
            self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        else:
            self.openai_client = None

        self.elevenlabs_client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

        os.makedirs(self.output_dir, exist_ok=True)

        self.last_track = None
        self.gpt_cache: Dict[str, str] = self._load_gpt_cache()

        logger.info("TYSA initialized successfully")

    def _load_gpt_cache(self) -> Dict[str, str]:
        """
        Load GPT announcement cache from JSON file

        Returns:
            Dictionary mapping cache keys to announcement strings
        """
        if not os.path.exists(self.gpt_cache_file):
            logger.info("No GPT cache file found, starting with empty cache")
            return {}

        try:
            with open(self.gpt_cache_file, 'r', encoding='utf-8') as f:
                cache = json.load(f)
            logger.info(f"Loaded GPT cache with {len(cache)} entries")
            return cache
        except Exception as e:
            logger.error(f"Failed to load GPT cache: {e}")
            return {}

    def _save_gpt_cache(self):
        """Save GPT announcement cache to JSON file"""
        try:
            with open(self.gpt_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.gpt_cache, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved GPT cache with {len(self.gpt_cache)} entries")
        except Exception as e:
            logger.error(f"Failed to save GPT cache: {e}")

    def _validate_env_vars(self):
        """Validate required environment variables"""
        required_vars = ['ELEVENLABS_API_KEY']

        # OpenAI only required for smart/wizard modes
        mode = os.getenv('MODE', 'smart').lower()
        if mode in ['smart', 'wizard']:
            required_vars.append('OPENAI_API_KEY')

        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for use in filenames by removing special characters and normalizing whitespace"""
        sanitized = re.sub(r'[^\w\s-]', '', text)
        sanitized = re.sub(r'[\s]+', '_', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        sanitized = sanitized.strip('_')
        return sanitized

    def get_current_track(self) -> Optional[Tuple[str, str]]:
        """
        Get currently playing track from Spotify using AppleScript (macOS only)

        Returns:
            Tuple of (song_name, artist_name) or None if nothing is playing
        """
        script = '''
        tell application "Spotify"
            if it is running then
                set trackName to name of current track
                set trackArtist to artist of current track
                return trackName & "|" & trackArtist
            end if
        end tell
        '''

        try:
            result = subprocess.run(
                ['osascript', '-e', script],
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0 and result.stdout.strip():
                output = result.stdout.strip()
                if '|' in output:
                    song, artist = output.split('|', 1)
                    return song.strip(), artist.strip()

        except subprocess.TimeoutExpired:
            logger.debug("Spotify AppleScript timeout")
        except subprocess.SubprocessError as e:
            logger.error(f"Error getting Spotify info: {e}")

        return None

    def generate_announcement(self, song: str, artist: str) -> str:
        """
        Generate complete announcement string based on mode
        Uses cache to avoid redundant API calls for smart/wizard modes

        Args:
            song: Original song title
            artist: Original artist name

        Returns:
            Complete announcement string ready for TTS
        """
        # BASIC MODE: No GPT, use user-provided strings
        if self.mode == 'basic':
            return f"{self.now_playing_text}: {song} - {self.by_text} - {artist}"

        # SMART/WIZARD MODE: Use GPT
        if not self.openai_client:
            logger.error("OpenAI client not initialized for smart/wizard mode")
            return f"Now playing: {song} - by - {artist}"

        cache_key = f"{song}|{artist}|{self.language_code}|{self.mode}"
        if cache_key in self.gpt_cache:
            cached_announcement = self.gpt_cache[cache_key]
            logger.info(f"Using cached announcement: {cached_announcement}")
            return cached_announcement

        system_prompt = f"""You are a radio announcer generating announcement text for text-to-speech.

MODE: {self.mode.upper()}
BASE LANGUAGE: {self.language_code}

Your job:
1. Simplify the song title and artist name (remove metadata, opus numbers, remaster notes, etc.)
2. Detect the primary language of the SIMPLIFIED song title and artist
3. Generate the complete announcement string with correct language brackets

SIMPLIFICATION RULES:
- For NORMAL SONGS: Keep FULL title ("Prepare for Landing" stays "Prepare for Landing")
- Remove ONLY metadata: "from [album]", "Remastered", "Radio Edit", "feat.", etc.

- For CLASSICAL MUSIC: Aggressively simplify!
  - Remove: ALL opus numbers (Op. 71, BWV 565, K. 331, RV 409, D. 960, Hob., etc.)
  - Remove: ALL movement numbers (I., II., III., IV., No. 13, etc.)
  - Remove: ALL tempo markings (Allegro, Andante, Moderato, Presto, Adagio, etc.)
  - Remove: ALL key signatures (in E Minor, in D Major, in B-flat, etc.)
  - Remove: Movement descriptions after colons
  - Keep: Only the main work title
  - Example: "Cello Concerto in E Minor, RV 409: II. Allegro" → "Cello Concerto"
  - Example: "Symphony No. 9 in D Minor, Op. 125: IV. Presto" → "Symphony No. 9"

- Shorten composer names: "Johann Sebastian Bach" → "Johann Bach"

ANNOUNCEMENT FORMAT:

If MODE is SMART:
- Uses eleven_flash_v2_5 which does NOT support brackets
- Translate "Now playing" and "by" to the BASE LANGUAGE
- NO BRACKETS AT ALL - just plain text
- Format: "[translated 'Now playing']: [song] - [translated 'by'] - [artist]"
- Example (BASE=sv): "Nu spelas: Bohemian Rhapsody - av - Queen"
- Example (BASE=en): "Now playing: Hakuna Matata - by - Johan Halldén"

If MODE is WIZARD:
- Uses eleven_v3 which supports brackets
- Translate "Now playing" and "by" to the BASE LANGUAGE
- Detect language of SIMPLIFIED title/artist, then use [read in XX] brackets
- Use [read in BASE] to switch back to base language between song and artist
- Add " - " before AND after "by"
- Format: "[translated 'Now playing']: [read in XX][simplified_song] [read in BASE] - [translated 'by'] - [read in XX][artist]"
- Example (BASE=sv, English song): "Nu spelas: [read in en]Gaia [read in sv] - av - [read in en]Oliver Ólafsson"
- Example (BASE=sv, Classical): "Nu spelas: [read in en]Cello Concerto [read in sv] - av - [read in it]Antonio Vivaldi"
- Example (BASE=en, Swedish song): "Now playing: [read in sv]Alla vill ju vara som du [read in en] - by - [read in sv]Nanne Grönvall"

Respond with ONLY the announcement string. No explanations."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{song} by {artist}"}
                ],
                max_tokens=150,
                temperature=0
            )

            content = response.choices[0].message.content
            if not content:
                logger.error("GPT returned empty content")
                return f"Now playing: {song} - by - {artist}"

            announcement = content.strip()
            logger.info(f"GPT generated announcement: {announcement}")

            # Cache the announcement
            self.gpt_cache[cache_key] = announcement
            self._save_gpt_cache()

            return announcement

        except Exception as e:
            logger.error(f"GPT announcement generation failed: {e}")
            # Fallback: simple announcement in base language
            return f"Now playing: {song} - by - {artist}"

    def _play_audio(self, file_path: str) -> bool:
        """Play audio file using macOS afplay command"""
        try:
            subprocess.run(
                ['afplay', '-v', str(self.volume), file_path],
                check=True,
                capture_output=True,
                timeout=30
            )
            logger.info(f"Played audio: {os.path.basename(file_path)}")
            return True
        except subprocess.TimeoutExpired:
            logger.error(f"Audio playback timed out: {file_path}")
            return False
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to play audio: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error playing audio: {e}")
            return False

    def generate_speech(self, text: str, output_filename: str, language_code: str, model_id: str) -> Optional[str]:
        """
        Generate speech using ElevenLabs

        Args:
            text: Text to convert to speech
            output_filename: Filename for the output audio
            language_code: Language code for TTS (ISO 639-1)
            model_id: ElevenLabs model ID to use

        Returns:
            Path to the generated audio file or None on failure
        """
        try:
            logger.info(f"Generating speech: '{text}'")

            audio = self.elevenlabs_client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=model_id,
                output_format="mp3_44100_128",
                language_code=language_code
            )

            audio_data = b''.join(chunk for chunk in audio)

            if not audio_data:
                logger.error("Received empty audio data from ElevenLabs")
                return None

            output_path = os.path.join(self.output_dir, output_filename)
            with open(output_path, 'wb') as f:
                f.write(audio_data)

            logger.info(f"Audio saved to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate speech: {e}")
            return None

    def process_current_track(self) -> bool:
        """
        Process the currently playing track

        Returns:
            True if a track was processed, False otherwise
        """
        track_info = self.get_current_track()
        if not track_info:
            return False

        song, artist = track_info
        track_identifier = f"{song}|{artist}"

        if track_identifier == self.last_track:
            logger.debug(f"Track already processed: {song} by {artist}")
            return False

        self.last_track = track_identifier

        # Generate complete announcement based on mode
        announcement = self.generate_announcement(song, artist)
        logger.info(f"Announcement ({self.mode}): {announcement}")

        # Determine model based on mode
        if self.mode == 'wizard':
            model_id = "eleven_v3"
        else:
            model_id = "eleven_flash_v2_5"

        # Create filename: mode_language_artist_song.mp3
        safe_artist = self._sanitize_filename(artist)
        safe_title = self._sanitize_filename(song)
        filename = f"{self.mode}_{self.language_code}_{safe_artist}_{safe_title}.mp3"
        file_path = os.path.join(self.output_dir, filename)

        if os.path.exists(file_path):
            logger.info(f"Audio file already exists: {filename} (skipping ElevenLabs)")
            self._play_audio(file_path)
            return True

        audio_path = self.generate_speech(announcement, filename, self.language_code, model_id)

        if audio_path:
            logger.info(f"Successfully processed track: {song} by {artist}")
            self._play_audio(audio_path)
            return True

        return False

    def run_continuous(self):
        """Run the announcer in continuous mode, polling for track changes"""
        logger.info(f"Starting continuous monitoring (polling every {self.poll_interval}s)")
        logger.info("Press Ctrl+C to stop")

        try:
            while True:
                self.process_current_track()
                time.sleep(self.poll_interval)

        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
        except Exception as e:
            logger.error(f"Unexpected error in continuous mode: {e}", exc_info=True)
            raise

    def run_once(self):
        """Run the announcer once for the current track"""
        logger.info("Running in single-shot mode")
        processed = self.process_current_track()

        if processed:
            logger.info("Track processed successfully")
        else:
            logger.info("No track to process")


def main():
    """Main entry point"""
    try:
        announcer = SpotifyAnnouncer()
        mode = os.getenv('RUN_MODE', 'continuous').lower()

        if mode == 'once':
            announcer.run_once()
        else:
            announcer.run_continuous()

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
