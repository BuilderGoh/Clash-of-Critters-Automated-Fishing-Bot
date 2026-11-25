# CrittersFishingBot v0.5.1

Requires the working v0.5 installation (with all prior vision patches). Stop the bot, copy these files into its folder and replace the existing files. No additional dependencies. Keep the existing Scrcpy server, launchers and templates.

Test one catch: `stream-live.bat --unknown-probe --timing-debug`

Continuous: `stream-continuous.bat --unknown-probe --timing-debug`

Diagnostic entries print raw detection, resolved target, predicted position/velocity, hit and latch. A raw tuple with None target bounds means the red marker was found but the yellow strip was not; raw=None means marker detection failed. Turn off --timing-debug for less log output. The new logic supports one-column targets with vertical support, limited occlusion reconstruction, duplicate-frame handling and narrow-target nearest-frame tolerance. It does not blindly click when no target is known. Automatic timing compensation is still recommended initially. F8 stops the bot.

Validated with synthetic narrow/occlusion tests and offline replay of the earlier 530-frame recording; live tiny-target accuracy is not yet measured. Use only where automation is permitted.
