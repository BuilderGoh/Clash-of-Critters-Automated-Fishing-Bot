# CrittersFishingBot v0.4.1

A local Python computer-vision fishing assistant for Clash of Critters on BlueStacks 5. Supports background operation using a persistent scrcpy video stream and ADB touch input, as well as raw ADB and foreground window modes. No AI API or subscription required.

## Quick start (Windows 10/11)

1. Install [Python](https://www.python.org/downloads/windows/) (3.12 recommended; 3.14 was used successfully by the original tester). Enable Python on PATH.
2. Download this repository as a ZIP and extract it, or clone it. Open CMD in the folder containing `bot.py`.
3. Run `setup.bat` to create the virtual environment and install dependencies.
4. Install FFmpeg: `winget install --id Gyan.FFmpeg -e`. Reopen CMD and verify with `ffmpeg -version`.
5. In BlueStacks 5, enable **Settings > Advanced > Android Debug Bridge (ADB)**. Keep it local to your computer. Default device is `127.0.0.1:5555`.
6. Run `setup-stream.bat`. It downloads the official scrcpy v3.3.4 server and verifies its SHA-256 checksum.
7. Open Clash of Critters and navigate to Fishing Contest. Use portrait orientation and keep the emulator rendering.

```bat
stream-snapshot.bat
stream-benchmark.bat
stream-dry-run.bat --unknown-probe
stream-live.bat --unknown-probe
```

Inspect the snapshot, then benchmark on an animated screen. Dry run makes no clicks; manually fish to verify detection. Live test stops after one catch or 60 seconds. Once verified, use:

```bat
stream-continuous.bat --unknown-probe
```

Continuous mode runs for up to 2,000 catches or 24 hours. Press **F8** or **Ctrl+C** to stop. Leave BlueStacks running behind other windows; minimised rendering is not guaranteed. Do not change Android resolution or orientation during a session.

## Launchers

| Launcher | Purpose |
| --- | --- |
| `setup.bat` | Install Python dependencies |
| `setup-stream.bat` | Download and verify scrcpy server |
| `stream-snapshot.bat` | Verify video capture |
| `stream-benchmark.bat` | Measure fresh frame delivery |
| `stream-dry-run.bat` | Observe without clicking |
| `stream-live.bat` | One-catch streaming test |
| `stream-continuous.bat` | Continuous streaming mode |
| `adb-*.bat` | Raw ADB screenshot alternatives |
| `dry-run.bat`, `live.bat` | Foreground window mode |

## Options and troubleshooting

- Start with automatic timing compensation. If clicks are consistently late, try `stream-continuous.bat --timing-lead-ms 100 --unknown-probe`. Adjust based on observed results; larger values can cause early clicks. Zero disables prediction.
- For a different ADB port, append `--serial 127.0.0.1:PORT` to the launcher command.
- `--unknown-probe` enables one experimental recovery tap after an unknown screen following reeling or rewards. Omit it to disable.
- If setup fails, install Python 3.12 and rerun setup. If FFmpeg is not found, reopen CMD after installation.
- If streaming fails, inspect `scrcpy-server.log` and `scrcpy-decoder.log`, verify ADB is enabled and try `adb-snapshot.bat`. The v0.4.1 port forwarding fix handles empty dynamic-port responses from older ADB implementations.
- Benchmark FPS is not end-to-end touch latency. ADB touch commands still have overhead.
- Foreground mode requires BlueStacks to stay focused and unmoved. Streaming mode does not use the physical mouse.

## Development

```bat
.venv\Scripts\python.exe -m unittest discover -v
```

The detector uses OpenCV, reward/title templates, state debouncing and predictive marker tracking. Casting and recognized reward dismissal retry every 500 ms. Fishing rod depletion detection is not implemented. Supervise initial runs and stop if unexpected screens appear.

## Credits and usage

Inspired by [Liamcky/CofCFishingBot](https://github.com/Liamcky/CofCFishingBot). Streaming uses the separately distributed [scrcpy v3.3.4](https://github.com/Genymobile/scrcpy/tree/v3.3.4) (Apache-2.0) and FFmpeg. Game artwork in the cropped detection templates belongs to its respective rights holders; no ownership is claimed. This project is unofficial and not affiliated with the game or emulator developers. Automated gameplay may violate game rules and lead to account penalties. Check the rules before use. No license for redistribution of third-party game assets is asserted.
