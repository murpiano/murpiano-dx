#!/usr/bin/env node

const path = require('node:path');
const { spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const result = spawnSync('bash', [path.join(root, 'murpiano-dx'), ...process.argv.slice(2)], {
  cwd: process.cwd(),
  env: process.env,
  stdio: 'inherit',
});

if (result.error) {
  console.error(`murpiano-dx: ${result.error.message}`);
  process.exit(1);
}

process.exit(result.status ?? 1);
