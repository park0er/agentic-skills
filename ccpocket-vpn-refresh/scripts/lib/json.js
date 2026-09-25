#!/usr/bin/env node
// Tiny JSON read/write helper used by the shell scripts.
// Usage:
//   node json.js get <file> <key>
//   node json.js set <file> <key> <value>
//   node json.js del <file> <key>

'use strict';
const fs = require('fs');

const [, , op, file, key, rawValue] = process.argv;

function readOrEmpty(path) {
  if (!fs.existsSync(path)) return {};
  try {
    return JSON.parse(fs.readFileSync(path, 'utf8'));
  } catch (e) {
    process.stderr.write(`json.js: failed to parse ${path}: ${e.message}\n`);
    process.exit(2);
  }
}

function coerce(v) {
  if (v === 'true') return true;
  if (v === 'false') return false;
  if (v === 'null') return null;
  if (/^-?\d+$/.test(v)) return parseInt(v, 10);
  if (/^-?\d+\.\d+$/.test(v)) return parseFloat(v);
  return v;
}

function atomicWrite(path, data) {
  const tmp = `${path}.tmp.${process.pid}`;
  fs.writeFileSync(tmp, data);
  fs.renameSync(tmp, path);
}

if (op === 'get') {
  if (!file || key === undefined) {
    process.stderr.write('usage: json.js get <file> <key>\n');
    process.exit(2);
  }
  const c = readOrEmpty(file);
  const v = c[key];
  if (v === undefined || v === null) process.exit(0);
  process.stdout.write(typeof v === 'object' ? JSON.stringify(v) : String(v));
} else if (op === 'set') {
  if (!file || !key || rawValue === undefined) {
    process.stderr.write('usage: json.js set <file> <key> <value>\n');
    process.exit(2);
  }
  const c = readOrEmpty(file);
  c[key] = coerce(rawValue);
  atomicWrite(file, JSON.stringify(c, null, 2) + '\n');
} else if (op === 'del') {
  if (!file || !key) {
    process.stderr.write('usage: json.js del <file> <key>\n');
    process.exit(2);
  }
  const c = readOrEmpty(file);
  delete c[key];
  atomicWrite(file, JSON.stringify(c, null, 2) + '\n');
} else {
  process.stderr.write('usage: json.js <get|set|del> <file> <key> [value]\n');
  process.exit(2);
}
