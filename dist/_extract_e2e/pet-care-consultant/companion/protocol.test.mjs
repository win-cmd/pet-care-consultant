import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_EVENT, STATE_PRESETS, normalizeEvent } from './protocol.mjs';

test('高危状态使用明确的非诊断提示', () => {
  const event = normalizeEvent({ pet: 'dog', state: 'critical' }, DEFAULT_EVENT);
  assert.equal(event.pet, 'dog');
  assert.equal(STATE_PRESETS[event.state].label, '危险后果演示');
  assert.match(event.message, /不代表宠物一定死亡/);
});

test('可切换猫并保留当前状态', () => {
  const current = normalizeEvent({ pet: 'dog', state: 'curious' }, DEFAULT_EVENT);
  const event = normalizeEvent({ pet: 'cat' }, current);
  assert.equal(event.pet, 'cat');
  assert.equal(event.state, 'curious');
});

test('拒绝未知宠物、状态和超长文本', () => {
  assert.throws(() => normalizeEvent({ pet: 'bird' }), /pet/);
  assert.throws(() => normalizeEvent({ state: 'dead' }), /state/);
  assert.throws(() => normalizeEvent({ message: 'x'.repeat(121) }), /120/);
});

test('移除控制字符且不把消息当 HTML', () => {
  const event = normalizeEvent({ message: '葡萄\u0000危险\n请送医' }, DEFAULT_EVENT);
  assert.equal(event.message, '葡萄 危险 请送医');
});
