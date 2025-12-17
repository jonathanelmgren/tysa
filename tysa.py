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

handlers = [logging.FileHandler('tysa.log')]
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

        self.enable_gpt = os.getenv('ENABLE_GPT_SIMPLIFICATION', 'true').lower() == 'true'
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'cjVigY5qzO86Huf0OWal')
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.output_dir = os.getenv('OUTPUT_DIR', 'output')
        self.poll_interval = int(os.getenv('POLL_INTERVAL_SECONDS', '1'))
        self.gpt_cache_file = os.getenv('GPT_CACHE_FILE', '.gpt_cache.json')
        self.volume = float(os.getenv('PLAYBACK_VOLUME', '0.5'))

        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')) if self.enable_gpt else None
        self.elevenlabs_client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

        os.makedirs(self.output_dir, exist_ok=True)

        self.last_track = None
        self.gpt_cache: Dict[str, Dict[str, str]] = self._load_gpt_cache()

        logger.info("TYSA initialized successfully")

    def _load_gpt_cache(self) -> Dict[str, Dict[str, str]]:
        """
        Load GPT simplification cache from JSON file

        Returns:
            Dictionary mapping raw track info to simplified versions
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
        """Save GPT simplification cache to JSON file"""
        try:
            with open(self.gpt_cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.gpt_cache, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved GPT cache with {len(self.gpt_cache)} entries")
        except Exception as e:
            logger.error(f"Failed to save GPT cache: {e}")

    def _validate_env_vars(self):
        """Validate required environment variables"""
        required_vars = ['ELEVENLABS_API_KEY']

        enable_gpt = os.getenv('ENABLE_GPT_SIMPLIFICATION', 'true').lower() == 'true'
        if enable_gpt:
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

    def simplify_title_with_gpt(self, song: str, artist: str) -> Tuple[str, str]:
        """
        Use GPT to simplify song titles for spoken announcements
        Uses cache to avoid redundant API calls
        If GPT is disabled, returns the original song and artist

        Args:
            song: Original song title
            artist: Original artist name

        Returns:
            Tuple of (simplified_song, simplified_artist)
        """
        if not self.enable_gpt or not self.openai_client:
            logger.debug("GPT simplification disabled, using original title")
            return song, artist

        cache_key = f"{song}|{artist}"
        if cache_key in self.gpt_cache:
            cached = self.gpt_cache[cache_key]
            logger.info(f"Using cached GPT simplification: {song} by {artist} → {cached['song']} by {cached['artist']}")
            return cached['song'], cached['artist']

        system_prompt = """You simplify song titles for a spoken radio announcement.

Remove ALL of the following:
- Opus numbers (Op. 71, Op.posth)
- Movement numbers (I., II., III., IV., No. 13)
- Act numbers (Act 2, Act II)
- Tempo markings (Allegro, Andante, Moderato, Presto, Adagio, Largo, Vivace, etc.)
- Catalog numbers (BWV 565, K. 331, D. 960, Hob., RV, etc.)
- Key signatures (in E Major, in D Minor, in B-flat Major, E-Dur, etc.)
- Scene descriptions (Scène, Danse des cygnes, etc.)
- Remaster notes (Remastered, 2023 Remaster, etc.)
- Version notes (Radio Edit, Extended Version, etc.)

Keep ONLY:
- The main piece name (Swan Lake, The Nutcracker, Moonlight Sonata)
- Recognizable subtitles (Waltz of the Flowers, Ode to Joy)

Shorten composer names:
- 'Pyotr Ilyich Tchaikovsky' → 'Pyotr Tchaikovsky'
- 'Johann Sebastian Bach' → 'Johann Bach'
- 'Ludwig van Beethoven' → 'Ludwig van Beethoven'
- 'Wolfgang Amadeus Mozart' → 'Wolfgang Mozart'

Respond with ONLY the simplified title and artist, formatted as: Title by Artist
No quotes, no extra text, no explanations."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{song} by {artist}"}
                ],
                max_tokens=100,
                temperature=0
            )

            result = response.choices[0].message.content.strip()
            logger.info(f"GPT simplification: {song} by {artist} → {result}")

            if " by " in result:
                simplified_song, simplified_artist = result.rsplit(" by ", 1)
                simplified_song = simplified_song.strip()
                simplified_artist = simplified_artist.strip()
            else:
                simplified_song = result
                simplified_artist = artist

            self.gpt_cache[cache_key] = {
                'song': simplified_song,
                'artist': simplified_artist
            }
            self._save_gpt_cache()

            return simplified_song, simplified_artist

        except Exception as e:
            logger.error(f"GPT simplification failed: {e}")
            return song, artist

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

    def generate_speech(self, text: str, output_filename: str) -> Optional[str]:
        """
        Generate speech using ElevenLabs

        Args:
            text: Text to convert to speech
            output_filename: Filename for the output audio

        Returns:
            Path to the generated audio file or None on failure
        """
        try:
            logger.info(f"Generating speech: '{text}'")

            audio = self.elevenlabs_client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
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

        simplified_song, simplified_artist = self.simplify_title_with_gpt(song, artist)
        announcement = f"Now playing: {simplified_song} - by {simplified_artist}"
        logger.info(f"Announcement: {announcement}")

        safe_artist = self._sanitize_filename(simplified_artist)
        safe_title = self._sanitize_filename(simplified_song)
        filename = f"{safe_artist}_{safe_title}.mp3"
        file_path = os.path.join(self.output_dir, filename)

        if os.path.exists(file_path):
            logger.info(f"Audio file already exists: {filename} (skipping ElevenLabs)")
            self._play_audio(file_path)
            return True

        audio_path = self.generate_speech(announcement, filename)

        if audio_path:
            logger.info(f"Successfully processed track: {simplified_song} by {simplified_artist}")
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
