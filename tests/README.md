# Recording container regression check

Run `python3 tests/test_recording_container.py` with Python 3, FFmpeg, and ffprobe
on PATH. FFmpeg needs the lavfi color/sine sources, libx264, libmp3lame, and AAC.
The test uses temporary synthetic media only. It does not access capture devices,
start the UI, alter the registry, or send a stream.

The check extracts the literal output suffix and audio codec choices from
`record_with_buttons.rb`, encodes MP3/AAC audio and MP4 video with/without audio,
checks the container and stream types, and decodes using the expected demuxer.
Temporary paths include spaces to exercise the output filename quotes.

This is a focused command/container check, not a Ruby or Windows integration
test. It does not cover JRuby/Swing, DirectShow input construction, device
selection, threading, or the bundled historical Windows FFmpeg version.
