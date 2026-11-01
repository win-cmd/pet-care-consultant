export const PETS = Object.freeze(['dog', 'cat']);
export const STATES = Object.freeze(['idle', 'happy', 'curious', 'worried', 'sick', 'critical', 'sleep']);

export const STATE_PRESETS = Object.freeze({
  idle: { label: '平静陪伴', severity: 'normal', defaultMessage: '我会陪你一起照顾毛孩子。' },
  happy: { label: '开心贴贴', severity: 'normal', defaultMessage: '问题解决了，开心一下。' },
  curious: { label: '好奇歪头', severity: 'info', defaultMessage: '让我听听你想了解什么。' },
  worried: { label: '有点担心', severity: 'warning', defaultMessage: '这里有些风险，需要认真留意。' },
  sick: { label: '不舒服', severity: 'warning', defaultMessage: '它现在不舒服，请按正文提示及时处理。' },
  critical: { label: '危险后果演示', severity: 'emergency', defaultMessage: '这是危险后果示意，不代表宠物一定死亡；请按正文警示处理。' },
  sleep: { label: '安静休息', severity: 'normal', defaultMessage: '先让毛孩子安静休息吧。' },
});

export const DEFAULT_EVENT = Object.freeze({
  pet: 'dog',
  state: 'idle',
  message: STATE_PRESETS.idle.defaultMessage,
  playSound: true,
});

export function normalizeEvent(input = {}, current = DEFAULT_EVENT) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) {
    throw new Error('事件必须是 JSON 对象');
  }

  const pet = input.pet ?? current.pet ?? DEFAULT_EVENT.pet;
  const state = input.state ?? current.state ?? DEFAULT_EVENT.state;
  if (!PETS.includes(pet)) throw new Error(`pet 只支持 ${PETS.join(' / ')}`);
  if (!STATES.includes(state)) throw new Error(`state 只支持 ${STATES.join(' / ')}`);

  const changedState = input.state !== undefined && input.state !== current.state;
  const changedPet = input.pet !== undefined && input.pet !== current.pet;
  let message = input.message ?? ((changedState || changedPet)
    ? STATE_PRESETS[state].defaultMessage
    : current.message ?? STATE_PRESETS[state].defaultMessage);
  if (typeof message !== 'string') throw new Error('message 必须是字符串');
  message = message.replace(/[\u0000-\u001f\u007f]/g, ' ').trim();
  if (!message) message = STATE_PRESETS[state].defaultMessage;
  if (message.length > 120) throw new Error('message 不能超过 120 个字符');

  const playSound = input.playSound ?? current.playSound ?? true;
  if (typeof playSound !== 'boolean') throw new Error('playSound 必须是布尔值');

  return { pet, state, message, playSound };
}
