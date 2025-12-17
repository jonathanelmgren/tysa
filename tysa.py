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
from typing import Optional, Tuple
from datetime import datetime

from openai import OpenAI
from elevenlabs import ElevenLabs, VoiceSettings
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('tysa.log')
    ]
)
logger = logging.getLogger(__name__)


class SpotifyAnnouncer:
    """Main class for TYSA - The Yapping Spotify Announcer"""

    def __init__(self):
        """Initialize the announcer with API clients"""
        load_dotenv()

        # Validate environment variables
        self._validate_env_vars()

        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

        # Initialize ElevenLabs client
        self.elevenlabs_client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))

        # Configuration
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'EXAVITQu4vr4xnSDxMaL')  # Default: Sarah
        self.model = os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
        self.output_dir = os.getenv('OUTPUT_DIR', 'output')
        self.poll_interval = int(os.getenv('POLL_INTERVAL_SECONDS', '5'))

        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)

        # Track the last processed song (song + artist combo)
        self.last_track = None

        logger.info("TYSA initialized successfully")

    def _validate_env_vars(self):
        """Validate required environment variables"""
        required_vars = [
            'OPENAI_API_KEY',
            'ELEVENLABS_API_KEY'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

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
                    logger.info(f"Current track: {song.strip()} by {artist.strip()}")
                    return song.strip(), artist.strip()

        except subprocess.TimeoutExpired:
            logger.debug("Spotify AppleScript timeout")
        except subprocess.SubprocessError as e:
            logger.error(f"Error getting Spotify info: {e}")

        return None

    def simplify_title_with_gpt(self, song: str, artist: str) -> Tuple[str, str]:
        """
        Use GPT to simplify song titles for spoken announcements

        Args:
            song: Original song title
            artist: Original artist name

        Returns:
            Tuple of (simplified_song, simplified_artist)
        """
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
- 'Pyotr Ilyich Tchaikovsky' → 'Tchaikovsky'
- 'Johann Sebastian Bach' → 'Bach'
- 'Ludwig van Beethoven' → 'Beethoven'
- 'Wolfgang Amadeus Mozart' → 'Mozart'

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
                return simplified_song.strip(), simplified_artist.strip()

            return result, artist

        except Exception as e:
            logger.error(f"GPT simplification failed: {e}")
            return song, artist

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

            # Generate audio
            audio = self.elevenlabs_client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=text,
                model_id="eleven_multilingual_v2",
                voice_settings=VoiceSettings(
                    stability=0.5,
                    similarity_boost=0.75,
                    style=0.0,
                    use_speaker_boost=True
                )
            )

            # Save audio to file
            output_path = os.path.join(self.output_dir, output_filename)
            with open(output_path, 'wb') as f:
                for chunk in audio:
                    f.write(chunk)

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
        # Get current track
        track_info = self.get_current_track()

        if not track_info:
            return False

        song, artist = track_info

        # Create a unique identifier for this track
        track_identifier = f"{song}|{artist}"

        # Skip if we've already processed this track
        if track_identifier == self.last_track:
            logger.debug(f"Track already processed: {song} by {artist}")
            return False

        # Update last track
        self.last_track = track_identifier

        # Simplify title and artist
        simplified_song, simplified_artist = self.simplify_title_with_gpt(song, artist)

        # Create announcement text
        announcement = f"Now playing: {simplified_song} by {simplified_artist}"
        logger.info(f"Announcement: {announcement}")

        # Generate filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"announcement_{timestamp}.mp3"

        # Generate speech
        audio_path = self.generate_speech(announcement, filename)

        if audio_path:
            logger.info(f"Successfully processed track: {simplified_song} by {simplified_artist}")
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

        # Check if we should run continuously or once
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
