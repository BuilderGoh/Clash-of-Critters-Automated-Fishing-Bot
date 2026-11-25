# v0.5 - Persistent Scrcpy touch input

Apply over v0.4.3 (or the consolidated v0.4.1 plus v0.4.2 and v0.4.3). Stop the bot before replacing files. This patch changes only bot.py, stream_backend.py and adds test_control.py; it leaves vision.py, timing.py, assets and launchers intact. No extra dependencies or server download are required if the v0.4.x streaming setup is already working. The server must be the pinned Scrcpy 3.3.4.

From Windows CMD in the bot directory:

```bat
stream-snapshot.bat
stream-dry-run.bat --unknown-probe
stream-live.bat --unknown-probe
stream-continuous.bat --unknown-probe
```

F8 or Ctrl+C stops the bot. Start with a supervised single-catch test. The stream now opens a persistent video socket followed by a control socket. The log should show `Persistent scrcpy control connected` and `Touch backend: persistent scrcpy control`. A dry run does not issue touches.

Automatic timing compensation uses the estimated video transport latency (35 ms by default), estimated device input latency (8 ms by default), and elapsed frame processing time. The `tap` field measures the local socket write duration only, not actual Android touch delivery. Do not assume a 0 ms write means zero end-to-end latency.

If needed, manually tune the total lead:

```bat
stream-live.bat --unknown-probe --timing-lead-ms 50
```

To use the previous video-only stream with ADB shell input:

```bat
stream-continuous.bat --unknown-probe --stream-input adb
```

The old adb-*.bat launchers still work. If control startup or sending fails, the program stops rather than silently sending another tap. Check scrcpy-server.log and scrcpy-decoder.log. The control path requires an encoded 720x1280 portrait stream for exact coordinate mapping. Other stream sizes can use the ADB fallback. Clipboard synchronization is disabled in control mode.

Unit tests:

```bat
.venv\Scripts\python.exe -m unittest discover -v
```

48 tests passed in the development environment, including 11 new control tests. Original 530-frame offline replay completed. Windows/BlueStacks control injection and actual device-side timing have not been live-tested. Game automation may violate game rules; use at your own risk.

Protocol source: https://github.com/Genymobile/scrcpy/tree/v3.3.4 (app/src/control_msg.c and server/src/main/java/com/genymobile/scrcpy/device/DesktopConnection.java).
