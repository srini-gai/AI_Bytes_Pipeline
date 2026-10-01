import {Config} from '@remotion/cli/config';
import {existsSync} from 'fs';
import {join} from 'path';
import {homedir} from 'os';

Config.setEntryPoint('./src/index.ts');
Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);

// Resolve the correct Chromium headless shell for this host.
// storage.googleapis.com is blocked on the VPS — Remotion cannot auto-download.
// We probe known install locations in priority order and use the first one found.
const CHROMIUM_REVISION = 'chromium_headless_shell-1194';
const CHROMIUM_BIN = 'chrome-linux/headless_shell';

function resolveChromium(): string | null {
  const candidates: string[] = [
    // 1. Playwright custom browsers path (set in cloud container via PLAYWRIGHT_BROWSERS_PATH)
    process.env['PLAYWRIGHT_BROWSERS_PATH']
      ? join(process.env['PLAYWRIGHT_BROWSERS_PATH'], CHROMIUM_REVISION, CHROMIUM_BIN)
      : '',
    // 2. Playwright default user cache (VPS running as root: /root/.cache/ms-playwright)
    join(homedir(), '.cache', 'ms-playwright', CHROMIUM_REVISION, CHROMIUM_BIN),
    // 3. Playwright default for non-root users
    join(homedir(), '.cache', 'ms-playwright', CHROMIUM_REVISION, CHROMIUM_BIN),
    // 4. System apt-installed chromium (Ubuntu 22.04)
    '/usr/bin/chromium-browser',
    '/usr/bin/chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
  ].filter(Boolean);

  for (const p of candidates) {
    if (existsSync(p)) {
      console.log(`[remotion.config] Using Chromium at: ${p}`);
      return p;
    }
  }

  console.warn('[remotion.config] No Chromium binary found — Remotion will attempt auto-download (may fail if storage.googleapis.com is blocked).');
  return null;
}

const chromiumPath = resolveChromium();
if (chromiumPath) {
  Config.setBrowserExecutable(chromiumPath);
}
