"""Check the recording command's output container using synthetic FFmpeg inputs.

This deliberately reads only the literal file-output suffix and audio codec map
from the Ruby source. It does not execute Ruby, Swing, DirectShow, or a device.
If command construction is refactored, update the extraction rather than silently
testing an independent copy of the output options.
"""

import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "configuration_setup_utility" / "record_with_buttons.rb"


def recording_options():
    source = SOURCE.read_text(encoding="utf-8")
    suffixes = re.findall(
        r'if should_save_file\?\s*\n\s*c \+= ("(?:\\.|[^"\\])*")',
        source,
    )
    if len(suffixes) != 1:
        raise AssertionError("Expected one literal file-output suffix")
    suffix = json.loads(suffixes[0])
    if suffix.count("#{@next_filename}") != 1:
        raise AssertionError("Expected one output filename interpolation")
    if "#{" in suffix.replace("#{@next_filename}", ""):
        raise AssertionError("Unexpected interpolation in the output suffix")
    mappings = re.findall(r"prefix_to_audio_codec = (\{[^\n]+\})", source)
    if len(mappings) != 1:
        raise AssertionError("Expected one audio codec map")
    codecs = dict(re.findall(r"'([^']+)'\s*=>\s*'([^']+)'", mappings[0]))
    if not {"mp3", "aac"}.issubset(codecs):
        raise AssertionError("Missing selectable audio codecs")
    return suffix, codecs


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "ffmpeg and ffprobe must be on PATH")
class RecordingContainerTest(unittest.TestCase):
    def check_container(self, extension, expected_format, video=False, audio=True):
        suffix, codecs = recording_options()
        with tempfile.TemporaryDirectory(prefix="recording container ") as temp:
            output = Path(temp) / ("1." + extension)
            command = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error"]
            if video:
                command += ["-f", "lavfi", "-i", "color=size=32x32:rate=10:duration=0.2"]
            if audio:
                command += ["-f", "lavfi", "-i", "sine=frequency=440:duration=0.2"]
            if video:
                command += ["-vcodec", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast"]
                if audio:
                    command += ["-acodec", "libmp3lame"]
            else:
                command += shlex.split(codecs[extension])
            command += shlex.split(suffix.replace("#{@next_filename}", str(output)))
            subprocess.run(command, check=True, capture_output=True, text=True)
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries",
                 "format=format_name:stream=codec_type,codec_name", "-of", "json", str(output)],
                check=True, capture_output=True, text=True,
            )
            metadata = json.loads(result.stdout)
            self.assertIn(expected_format, metadata["format"]["format_name"].split(","))
            self.assertEqual(sorted(s["codec_type"] for s in metadata["streams"]),
                             sorted((["video"] if video else []) + (["audio"] if audio else [])))
            # An extension-specific consumer must also be able to decode the file.
            subprocess.run(
                ["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-f", expected_format,
                 "-i", str(output), "-f", "null", "-"],
                check=True, capture_output=True, text=True,
            )

    def test_mp3_audio(self):
        self.check_container("mp3", "mp3")

    def test_aac_audio(self):
        self.check_container("aac", "aac")

    def test_mp4_video(self):
        self.check_container("mp4", "mov", video=True, audio=False)

    def test_mp4_video_and_audio(self):
        self.check_container("mp4", "mov", video=True)


if __name__ == "__main__":
    unittest.main()
