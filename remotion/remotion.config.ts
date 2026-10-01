import {Config} from '@remotion/cli/config';

Config.setEntryPoint('./src/index.ts');
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);

// Use the pre-installed Playwright Chromium headless shell
// (storage.googleapis.com is blocked — auto-download won't work)
// Apply unconditionally: the binary exists at this path on the VPS regardless of NODE_ENV
Config.setBrowserExecutable('/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell');
