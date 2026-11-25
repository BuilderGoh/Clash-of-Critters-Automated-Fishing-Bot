# 🎣 CrittersFishingBot

An automatic fishing bot for Clash of Critters on BlueStacks 5. Fish in the background while using your computer normally. No AI subscription or API key required.

**Version: v0.5.1 | Windows 10/11 | BlueStacks 5**

## What it does

- Automatically casts, reels and dismisses reward screens, including personal and team records.
- Runs behind other Windows applications using persistent Scrcpy video and touch sockets.
- Predicts marker movement and handles narrow or briefly obscured yellow targets.
- Retries casting and reward dismissal every 0.5 seconds.
- Includes F8 emergency stop and alternative ADB input.

> Use the complete v0.5.1 source tree, not the v0.5.1 patch ZIP alone. If updating an older installation, apply the intervening patches in order before v0.5.1.

## First-time setup (only do this once)

### Step 1 — Install Python

Open Command Prompt (press `Windows + R`, type `cmd`, press Enter). Copy and paste:

```cmd
winget install --id Python.Python.3.12 -e
```

If prompted, accept the installation. Alternatively, download [Python](https://www.python.org/downloads/windows/) and select **Add Python to PATH** in the installer.

### Step 2 — Install FFmpeg

In Command Prompt, copy and paste:

```cmd
winget install --id Gyan.FFmpeg -e
```

Close Command Prompt and open a new one. Verify both installations:

```cmd
py --version
ffmpeg -version
```

### Step 3 — Download the bot

On this GitHub repository, click the green **Code** button, then **Download ZIP**. Right-click the downloaded ZIP and select **Extract All**.

Open the extracted folder containing `bot.py` and `setup.bat`. Click the File Explorer address bar, type `cmd`, and press Enter. This opens Command Prompt in the correct folder, regardless of where you extracted the ZIP.

### Step 4 — Install the bot

Copy and paste the following commands one at a time. Wait for each to finish and press any key when prompted.

```cmd
setup.bat
```

```cmd
setup-stream.bat
```

The first installs Python dependencies; the second downloads and verifies the official scrcpy v3.3.4 server. You do not need to install scrcpy separately.

### Step 5 — Configure BlueStacks

Open BlueStacks 5 → **Settings → Advanced → Android Debug Bridge (ADB)**. Enable ADB and save changes. The default address is `127.0.0.1:5555`. Keep ADB local to your computer.

Open Clash of Critters, navigate to Fishing Contest and use portrait orientation. Leave BlueStacks running. The persistent control backend expects a 720 × 1280 encoded stream; the default streaming configuration requests this size.

### Step 6 — Test the bot

In the bot folder's Command Prompt, run:

```cmd
stream-snapshot.bat
```

Open the generated `stream-snapshot.png` and confirm it shows your game. Then run:

```cmd
stream-live.bat --unknown-probe
```

Look for `Persistent scrcpy control connected` and `Touch backend: persistent scrcpy control` in the console. This test stops after one catch or 60 seconds. Watch it complete a fishing cycle before proceeding.

## Start fishing (every time)

Open BlueStacks and navigate to Fishing Contest. Open Command Prompt in the bot folder (type `cmd` in the File Explorer address bar), then copy and paste:

```cmd
stream-continuous.bat --unknown-probe
```

That's it! The bot can fish while you use other windows. Leave BlueStacks running behind them; minimised operation is not guaranteed. The session stops after 2,000 catches or 24 hours, whichever comes first.

**To stop:** press **F8** or focus the Command Prompt and press **Ctrl+C**.

> The optional `--unknown-probe` enables a single experimental recovery tap after an unrecognised post-fishing screen. Remove it if you prefer not to allow that tap.

## Troubleshooting

### Bot clicks too early or too late

Start with automatic timing compensation (the default). If clicks are consistently late, try:

```cmd
stream-continuous.bat --timing-lead-ms 50 --unknown-probe
```

Adjust the number based on results. A larger number clicks earlier; zero disables prediction. A high lead is not necessarily better.

### Bot misses small yellow targets

Use the latest v0.5.1 files and start with automatic timing compensation. To collect detailed diagnostics, run:

```cmd
stream-live.bat --unknown-probe --timing-debug
```

The logs show raw marker and target detection, reconstructed target, predicted position, hit decision and click latch. A raw tuple with missing target bounds means the marker was found but the yellow strip was not; `raw=None` means marker detection failed. Remove `--timing-debug` for normal operation.

### Video works but the bot does not tap

Keep the fast video stream but switch to the previous ADB touch backend:

```cmd
stream-live.bat --unknown-probe --stream-input adb
```

If the test succeeds:

```cmd
stream-continuous.bat --unknown-probe --stream-input adb
```

### Bot gets stuck on a reward screen

Ensure you have the latest vision files. Recognised reward screens are retried every 0.5 seconds. The optional unknown probe is limited to a single recovery tap; it is not unrestricted clicking. If the screen remains stuck, stop the bot and capture a screenshot for troubleshooting.

### Bot cannot connect to BlueStacks

Check that ADB is enabled and BlueStacks is running. If your ADB port is different, replace `5555` below with the port shown in BlueStacks settings:

```cmd
stream-continuous.bat --serial 127.0.0.1:5555 --unknown-probe
```

### The system cannot find the path specified

Open CMD in the folder containing `bot.py`, then run `setup.bat` again. If setup fails, install Python 3.12 and retry.

### FFmpeg is not recognised

Close and reopen Command Prompt after installing FFmpeg. Run `ffmpeg -version` to check, then rerun `setup-stream.bat`.

### Streaming fails

Check `scrcpy-server.log` and `scrcpy-decoder.log` if present. Test raw ADB capture:

```cmd
adb-snapshot.bat
```

If raw ADB works, you can try the slower alternative:

```cmd
adb-live.bat --unknown-probe
```

After a successful test:

```cmd
adb-continuous.bat --unknown-probe
```

Raw ADB capture may have higher latency during timed reeling. For foreground mode, `live.bat` requires BlueStacks to remain focused and unmoved.

## Optional diagnostic commands

| Command | Purpose |
| --- | --- |
| `stream-benchmark.bat` | Measure fresh video frame delivery on an animated screen |
| `stream-dry-run.bat --unknown-probe` | Test detection while manually fishing; no automatic clicks |
| `.venv\Scripts\python.exe -m unittest discover -v` | Run unit tests |

## Important notes

- Fishing rod depletion detection is not implemented. Supervise initial sessions.
- Do not change Android resolution or orientation during a session.
- If the game stops rendering when minimised, restore BlueStacks and leave it behind other windows.
- Benchmark FPS and logged socket-write durations are not end-to-end touch latency. ADB fallback has additional subprocess overhead. Start with automatic timing compensation; do not assume a 0 ms socket write means instant in-game input.
- This unofficial project is not affiliated with Clash of Critters or BlueStacks. Automation may violate game rules and lead to account penalties. Check the rules before using it.

## Updating an existing installation

Stop the bot with F8 or Ctrl+C. Back up your current folder. If you already have v0.5 with all previous patches, extract the v0.5.1 patch into the folder containing `bot.py`, replacing matching files. No additional dependencies are needed. Keep your existing launchers, templates and pinned Scrcpy server. Run the one-catch test again before continuous operation.

## Changelog

| Version | Changes |
| --- | --- |
| v0.5.1 | Narrow target detection, short-term occlusion recovery, duplicate-frame handling and timing diagnostics. |
| v0.5 | Persistent Scrcpy touch socket and ADB input fallback. |
| v0.4.3 | Generalised reward screen recognition, including team records. |
| v0.4.2 | Improved narrow target handling and reward detection. |
| v0.4.1 | Compatibility fix for ADB port forwarding. |
| v0.4 | Persistent Scrcpy video streaming. |

## Testing

The v0.5.1 development build was reported to pass 64 unit tests and replay the original 530-frame gameplay recording. Synthetic narrow-target and occlusion tests do not guarantee live catch accuracy across machines or game versions.

## Credits

Inspired by [Liamcky/CofCFishingBot](https://github.com/Liamcky/CofCFishingBot). Uses OpenCV, [scrcpy v3.3.4](https://github.com/Genymobile/scrcpy/tree/v3.3.4) (Apache-2.0), and FFmpeg. Game artwork in cropped detection templates belongs to its respective rights holders; no ownership or redistribution license for those assets is asserted.
