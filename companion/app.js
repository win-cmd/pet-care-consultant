import { DEFAULT_EVENT, PETS, STATE_PRESETS, STATES, normalizeEvent } from './protocol.mjs';

const stage = document.querySelector('#stage');
const notice = document.querySelector('#notice');
const stateLabel = document.querySelector('#state-label');
const petMessage = document.querySelector('#pet-message');
const speech = document.querySelector('#speech');
const connection = document.querySelector('#connection');
const latency = document.querySelector('#latency');
const soundToggle = document.querySelector('#sound-toggle');
const motionToggle = document.querySelector('#motion-toggle');
const petTitle = document.querySelector('#pet-title');
const petDesc = document.querySelector('#pet-desc');
let current = { ...DEFAULT_EVENT };
let audioContext;
let soundEnabled = false;
let hasReceivedPetEvent = false;

const petNames = { dog: '小狗', cat: '小猫' };

function render(event, measureLatency = true) {
  current = event;
  const preset = STATE_PRESETS[event.state];
  stage.dataset.pet = event.pet;
  stage.dataset.state = event.state;
  notice.dataset.severity = preset.severity;
  stateLabel.textContent = `${petNames[event.pet]} · ${preset.label}`;
  petMessage.textContent = event.message;
  speech.textContent = event.state === 'critical' ? '请先看正文里的紧急提醒' : event.state === 'happy' ? '太好啦' : event.state === 'curious' ? '让我想一想' : event.state === 'sleep' ? '安静休息一下' : event.state === 'worried' || event.state === 'sick' ? '我有点不舒服' : '今天也要科学养宠哦';
  petTitle.textContent = `动态${petNames[event.pet]}`;
  petDesc.textContent = `一只可爱的二次元${petNames[event.pet]}，当前状态为${preset.label}。${event.message}`;
  document.querySelectorAll('[data-pet-choice]').forEach((button) => {
    button.setAttribute('aria-pressed', String(button.dataset.petChoice === event.pet));
  });
  document.querySelectorAll('[data-state]').forEach((button) => {
    if (button.tagName === 'BUTTON') button.setAttribute('aria-pressed', String(button.dataset.state === event.state));
  });
  if (event.sentAt && measureLatency) latency.textContent = `联动 ${Math.max(0, Date.now() - event.sentAt)} ms`;
  if (!measureLatency) latency.textContent = '等待新事件';
}

function setConnection(text, className = '') {
  connection.textContent = text;
  connection.className = `connection ${className}`.trim();
}

for (const state of STATES) {
  const button = document.createElement('button');
  button.type = 'button';
  button.dataset.state = state;
  button.textContent = STATE_PRESETS[state].label;
  button.setAttribute('aria-pressed', String(state === current.state));
  button.addEventListener('click', () => sendManual({ state, playSound: true }));
  document.querySelector('#state-buttons').append(button);
}

async function sendManual(change) {
  const input = { ...change, pet: change.pet ?? current.pet };
  if (location.protocol === 'file:') {
    const event = normalizeEvent(input, current);
    render(event);
    if (soundEnabled && event.playSound) playPetSound(event.pet, event.state);
    return;
  }
  try {
    const response = await fetch('./event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(input),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error);
    render(result.event);
  } catch (error) {
    setConnection('演示发送失败', 'offline');
    petMessage.textContent = error.message;
  }
}

document.querySelectorAll('[data-pet-choice]').forEach((button) => {
  button.addEventListener('click', () => {
    const pet = button.dataset.petChoice;
    sendManual({ pet, state: 'happy', message: `已切换成${petNames[pet]}，我会用不同的动作和叫声陪你。`, playSound: true });
  });
});

function tone(startFrequency, endFrequency, offset, duration, type = 'sine', volume = 0.07) {
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  const start = audioContext.currentTime + offset;
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(startFrequency, start);
  oscillator.frequency.exponentialRampToValueAtTime(Math.max(20, endFrequency), start + duration);
  gain.gain.setValueAtTime(0.001, start);
  gain.gain.exponentialRampToValueAtTime(volume, start + 0.025);
  gain.gain.exponentialRampToValueAtTime(0.001, start + duration);
  oscillator.connect(gain).connect(audioContext.destination);
  oscillator.start(start);
  oscillator.stop(start + duration + 0.02);
}

function bark(offset = 0) {
  tone(230, 85, offset, 0.14, 'sawtooth', 0.055);
  tone(140, 70, offset + 0.02, 0.12, 'square', 0.025);
}

function meow(offset = 0, worried = false) {
  tone(worried ? 690 : 480, worried ? 310 : 760, offset, 0.24, 'triangle', 0.06);
  tone(worried ? 560 : 740, worried ? 280 : 390, offset + 0.22, 0.34, 'triangle', 0.05);
}

function playPetSound(pet, state) {
  if (!audioContext || !soundEnabled || state === 'idle') return;
  if (state === 'happy') {
    if (pet === 'dog') { bark(0); bark(0.2); } else meow(0);
  } else if (state === 'curious') {
    if (pet === 'dog') bark(0); else meow(0);
  } else if (state === 'worried' || state === 'sick') {
    if (pet === 'dog') tone(670, 260, 0, 0.65, 'sine', 0.045); else meow(0, true);
  } else if (state === 'critical') {
    tone(660, 660, 0, 0.12, 'square', 0.035);
    tone(660, 660, 0.22, 0.12, 'square', 0.035);
    if (pet === 'dog') tone(520, 180, 0.42, 0.6, 'sine', 0.04); else meow(0.4, true);
  } else if (state === 'sleep' && pet === 'cat') {
    for (let i = 0; i < 5; i += 1) tone(75, 65, i * 0.12, 0.1, 'sawtooth', 0.018);
  }
}

soundToggle.addEventListener('click', async () => {
  if (!audioContext) {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!AudioContext) {
      document.querySelector('#sound-hint').textContent = '这个浏览器不支持合成音效，动态画面仍可使用。';
      return;
    }
    audioContext = new AudioContext();
  }
  await audioContext.resume();
  soundEnabled = !soundEnabled;
  soundToggle.textContent = soundEnabled ? '关闭声音' : '开启声音';
  soundToggle.classList.toggle('enabled', soundEnabled);
  document.querySelector('#sound-hint').textContent = soundEnabled ? '声音已开启。猫狗会使用不同的合成叫声。' : '声音已关闭。';
  if (soundEnabled) playPetSound(current.pet, 'happy');
});

motionToggle.addEventListener('click', () => {
  const reduced = document.body.classList.toggle('reduce-motion');
  motionToggle.setAttribute('aria-pressed', String(reduced));
  motionToggle.textContent = reduced ? '恢复动态' : '减少动态';
});

if (location.protocol !== 'file:' && 'EventSource' in window) {
  const events = new EventSource('./events');
  events.addEventListener('open', () => setConnection('实时联动中', 'online'));
  events.addEventListener('pet', (message) => {
    try {
      const event = JSON.parse(message.data);
      const measureLatency = hasReceivedPetEvent;
      hasReceivedPetEvent = true;
      render(event, measureLatency);
      if (soundEnabled && event.playSound) playPetSound(event.pet, event.state);
    } catch {
      setConnection('事件格式异常', 'offline');
    }
  });
  events.addEventListener('error', () => setConnection('等待重新连接', 'offline'));
} else {
  setConnection('手动演示模式', 'offline');
  latency.textContent = '打开本地服务后可联动';
}

render(current);
