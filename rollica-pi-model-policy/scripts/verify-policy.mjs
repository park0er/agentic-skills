#!/usr/bin/env node
// Exercise Pi's real adapters without reading or writing the user's Pi profile.
import { readFile, writeFile } from 'node:fs/promises';
import { resolve, join } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

const { values } = parseArgs({ options: {
  policy: { type: 'string' }, 'sdk-dir': { type: 'string' }, report: { type: 'string' },
  live: { type: 'boolean', default: false }, model: { type: 'string' },
  tools: { type: 'boolean', default: false },
} });
if (!values.policy || !values['sdk-dir']) throw new Error('Required: --policy FILE --sdk-dir PI_AI_PACKAGE_DIR [--live] [--tools] [--model OWNER/ID] [--report FILE]');
if (values.live && !process.env.MIFY_API_KEY) throw new Error('Missing MIFY_API_KEY; do not put credentials in the policy or command arguments');
const sdk = resolve(values['sdk-dir']);
const metadata = JSON.parse(await readFile(join(sdk, 'package.json'), 'utf8'));
const { getSupportedThinkingLevels, clampThinkingLevel } = await import(pathToFileURL(join(sdk, 'dist/models.js')));
const policy = JSON.parse(await readFile(resolve(values.policy), 'utf8'));
const allLevels = ['off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'];
const rows = [];
const jobs = [];
const seen = new Set();
for (const endpoint of policy.endpoints) for (const route of endpoint.routes) {
  const catalog = policy.catalogs.find(c => c.id === route.catalogId);
  if (!catalog) throw new Error(`Missing catalog ${route.catalogId}`);
  // This verifier sends credentials only to Mify. Other gateways need their own explicit verifier.
  if (endpoint.host.kind !== 'exact' || endpoint.host.value !== 'api.llm.mioffice.cn') throw new Error('Verifier only allows the exact Mify host');
  const baseUrl = `https://${endpoint.host.value}${route.canonicalBasePath ?? route.path.value}`;
  for (const definition of catalog.models.filter(m => m.enabled && (!values.model || m.id === values.model))) {
    const identity = `${route.api}:${baseUrl}:${definition.id}`;
    if (seen.has(identity)) continue;
    seen.add(identity);
    if (definition.reasoning === true && allLevels.some(l => !(l in (definition.thinkingLevelMap ?? {})))) throw new Error(`Reasoning candidate ${definition.id} must explicitly declare all seven thinking levels`);
    const model = { input: ['text'], contextWindow: 128000, maxTokens: 8192,
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 }, ...definition,
      provider: endpoint.provider.id, baseUrl, api: route.api };
    for (const level of getSupportedThinkingLevels(model)) jobs.push({ model, level });
    jobs.push({ model, level: clampThinkingLevel(model, 'medium'), defaultLevel: true });
    if (values.tools) jobs.push({ model, level: clampThinkingLevel(model, 'medium'), toolTest: true });
  }
}
if (!jobs.length) throw new Error('No matching models');
async function run({ model, level, defaultLevel = false, toolTest = false }) {
  const { streamSimple } = await import(pathToFileURL(join(sdk, `dist/api/${model.api}.js`)));
  const row = { model: model.id, api: model.api, level, defaultLevel, toolTest, pass: false };
  const context = { systemPrompt: toolTest ? 'Call policy_probe exactly once with value "OK". After its result, reply exactly OK and do not call any more tools.' : 'Follow user instructions.',
    messages: [{ role: 'user', content: toolTest ? 'Use policy_probe to return OK.' : 'Reply exactly OK', timestamp: Date.now() }],
    ...(toolTest ? { tools: [{ name: 'policy_probe', description: 'Return a test value; has no side effects.', parameters: { type: 'object', properties: { value: { type: 'string' } }, required: ['value'], additionalProperties: false } }] } : {}) };
  let payload;
  const options = { apiKey: values.live ? process.env.MIFY_API_KEY : 'dry-run-placeholder',
    ...(level === 'off' ? {} : { reasoning: level }), maxTokens: 4096,
    signal: AbortSignal.timeout(60000),
    onPayload: p => { payload = p; if (!values.live) throw new Error('DRY_RUN_CAPTURED'); } };
  try {
    const first = await streamSimple(model, context, options).result();
    if (!payload) throw new Error(first.errorMessage || 'Pi did not build a request');
    row.wire = { role: payload.messages?.[0]?.role, reasoning_effort: payload.reasoning_effort, thinking: payload.thinking, output_config: payload.output_config };
    const mapped = model.thinkingLevelMap?.[level];
    if (model.api === 'openai-completions') {
      if (payload.messages[0].role !== 'system') throw new Error('Expected system role');
      if (model.reasoning && payload.reasoning_effort !== mapped) throw new Error(`Expected wire effort ${mapped}, got ${payload.reasoning_effort}`);
    } else if (model.reasoning && level === 'off') {
      if (payload.thinking?.type !== 'disabled') throw new Error('Expected disabled thinking');
    } else if (model.reasoning && model.compat?.forceAdaptiveThinking) {
      if (payload.thinking?.type !== 'adaptive' || payload.output_config?.effort !== mapped) throw new Error('Adaptive effort mapping mismatch');
    }
    if (!values.live) { row.pass = true; return row; }
    if (first.stopReason === 'error' || first.stopReason === 'aborted') throw new Error(first.errorMessage || first.stopReason);
    let result = first;
    if (toolTest) {
      const calls = first.content.filter(c => c.type === 'toolCall');
      if (calls.length !== 1 || calls[0].name !== 'policy_probe' || calls[0].arguments?.value !== 'OK') throw new Error('Expected one valid policy_probe call');
      context.messages.push(first, { role: 'toolResult', toolCallId: calls[0].id, toolName: calls[0].name,
        content: [{ type: 'text', text: 'OK' }], isError: false, timestamp: Date.now() });
      result = await streamSimple(model, context, { ...options, signal: AbortSignal.timeout(60000) }).result();
      if (result.stopReason === 'error' || result.stopReason === 'aborted') throw new Error(result.errorMessage || result.stopReason);
    }
    const text = result.content.filter(c => c.type === 'text').map(c => c.text).join('');
    row.stopReason = result.stopReason;
    row.hasText = text.trim().length > 0;
    row.hasThinking = result.content.some(c => c.type === 'thinking' && c.thinking.length > 0);
    row.pass = row.hasText && result.stopReason === 'stop';
    if (!row.pass) row.error = 'No completed text reply';
  } catch (error) {
    // Error bodies may contain sensitive headers; sanitize before persisting.
    row.error = String(error.message).replaceAll(process.env.MIFY_API_KEY || 'NEVER_A_REAL_TOKEN', '[REDACTED]').slice(0, 600);
  }
  return row;
}
await Promise.all([0, 1, 2].map(async () => {
  while (jobs.length) {
    const row = await run(jobs.shift()); rows.push(row); console.log(JSON.stringify(row));
  }
}));
const report = { revision: policy.revision, piVersion: metadata.version, testedAt: new Date().toISOString(), live: values.live,
  passed: rows.filter(r => r.pass).length, total: rows.length, rows,
  limitation: 'Successful requests verify Pi wire format and gateway acceptance, not whether distinct accepted effort values produce distinct model compute budgets.' };
if (values.report) await writeFile(resolve(values.report), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ passed: report.passed, total: report.total, live: report.live }));
if (report.passed !== report.total) process.exitCode = 1;
