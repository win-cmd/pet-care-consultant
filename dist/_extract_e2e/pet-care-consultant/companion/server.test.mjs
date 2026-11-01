import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { listen } from './server.mjs';

const execFileAsync = promisify(execFile);

test('本地事件通过 SSE 推送，CLI 可切换猫狗危险状态', async (t) => {
  const server = await listen(0);
  const address = server.address();
  const base = `http://127.0.0.1:${address.port}`;
  const controller = new AbortController();
  t.after(() => controller.abort());
  t.after(() => new Promise((resolve) => server.close(resolve)));

  const health = await fetch(`${base}/health`).then((response) => response.json());
  assert.equal(health.app, 'pet-care-companion');

  const page = await fetch(base);
  assert.equal(page.status, 200);
  assert.match(page.headers.get('content-security-policy'), /default-src 'self'/);
  assert.match(await page.text(), /二次元搭档/);

  const events = await fetch(`${base}/events`, { signal: controller.signal });
  assert.equal(events.headers.get('content-type'), 'text/event-stream; charset=utf-8');
  const reader = events.body.getReader();
  const decoder = new TextDecoder();
  let received = '';
  received += decoder.decode((await reader.read()).value, { stream: true });
  assert.match(received, /event: pet/);

  const { stdout } = await execFileAsync(process.execPath, ['companion/pet.mjs', '--pet', 'dog', '--state', 'critical', '--message', '葡萄危险后果演示，请按正文立即处理'], {
    cwd: process.cwd(),
    env: { ...process.env, PET_COMPANION_URL: base },
  });
  assert.match(stdout, /dog \/ critical/);

  while (!received.includes('葡萄危险后果演示')) {
    const { value, done } = await reader.read();
    if (done) break;
    received += decoder.decode(value, { stream: true });
  }
  assert.match(received, /"state":"critical"/);
  assert.match(received, /葡萄危险后果演示/);

  const catResponse = await fetch(`${base}/event`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pet: 'cat', state: 'happy' }),
  });
  const cat = await catResponse.json();
  assert.equal(cat.event.pet, 'cat');
  assert.equal(cat.event.state, 'happy');

  const invalid = await fetch(`${base}/event`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ state: 'dead' }),
  });
  assert.equal(invalid.status, 400);
});
