import {Config} from '@remotion/cli/config';

Config.setEntryPoint('./src/index.ts');
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);

// Use the pre-installed Playwright Chromium in CI / cloud container
// (storage.googleapis.com is blocked in this environment)
const PLAYWRIGHT_CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
if (process.env.NODE_ENV !== 'production') {
  Config.setBrowserExecutable(PLAYWRIGHT_CHROME);
}
