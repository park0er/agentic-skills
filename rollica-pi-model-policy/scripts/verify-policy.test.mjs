import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

test('non-reasoning models support both protocols without network or thinking maps', { skip: !process.env.PI_TEST_SDK_DIR }, async () => {
  const dir = await mkdtemp(join(tmpdir(), 'pi-policy-skill-test-'));
  try {
    const policy = { revision: 'test', endpoints: [{ host: { kind: 'exact', value: 'api.llm.mioffice.cn' }, provider: { id: 'mify' }, routes: [
      { api: 'openai-completions', path: { value: '/v1' }, catalogId: 'plain' },
      { api: 'anthropic-messages', path: { value: '/anthropic' }, catalogId: 'plain' },
    ] }], catalogs: [{ id: 'plain', models: [{ id: 'test/plain', name: 'Plain', enabled: true, reasoning: false }] }] };
    await writeFile(join(dir, 'policy.json'), JSON.stringify(policy));
    const result = spawnSync(process.execPath, [fileURLToPath(new URL('./verify-policy.mjs', import.meta.url)), '--policy', join(dir, 'policy.json'), '--sdk-dir', process.env.PI_TEST_SDK_DIR, '--tools', '--report', join(dir, 'report.json')], { encoding: 'utf8', timeout: 20000 });
    assert.equal(result.status, 0, result.stdout + result.stderr);
    const report = JSON.parse(await readFile(join(dir, 'report.json'), 'utf8'));
    assert.equal(report.live, false);
    assert.equal(report.total, 6);
    assert.equal(report.passed, 6);
    assert.ok(report.rows.every(r => r.level === 'off'));
  } finally { await rm(dir, { recursive: true, force: true }); }
});
