// Post-export step: make dist/index.html an installable iOS/Android PWA.
// Runs after `expo export -p web` (see the build:web script).
import { readFileSync, writeFileSync } from 'node:fs';

const file = 'dist/index.html';
let html = readFileSync(file, 'utf8');

const head = `
    <link rel="manifest" href="/manifest.webmanifest" />
    <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-status-bar-style" content="default" />
    <meta name="apple-mobile-web-app-title" content="ORBOU" />
    <style>html, body { background: #F0E8DC; }</style>`;

const register = `
  <script>
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', function () { navigator.serviceWorker.register('/sw.js'); });
    }
  </script>`;

if (!html.includes('rel="manifest"')) {
  html = html
    .replace('</head>', `${head}\n</head>`)
    // viewport-fit=cover lets the app draw under the notch; safe-area insets keep content clear.
    .replace('initial-scale=1, shrink-to-fit=no', 'initial-scale=1, viewport-fit=cover')
    .replace('</body>', `${register}\n</body>`);
  writeFileSync(file, html);
}
console.log('PWA tags injected into', file);
