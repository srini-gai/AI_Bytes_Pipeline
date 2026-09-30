import {Config} from '@remotion/cli/config';

Config.setEntryPoint('./src/index.ts');
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);

// Use the pre-installed Playwright Chromium in CI / cloud container
// (storage.googleapis.com is blocked in this environment)
const PLAYWRIGHT_CHROME = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';
if (process.env.NODE_ENV !== 'production') {
  Config.setBrowserExecutable(PLAYWRIGHT_CHROME);
}
