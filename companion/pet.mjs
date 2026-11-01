import { PETS, STATES } from './protocol.mjs';

function usage() {
  console.log(`用法：node companion/pet.mjs [--pet dog|cat] [--state ${STATES.join('|')}] [--message "短提示"] [--quiet]\n宠物：${PETS.join(' / ')}`);
}

function parseArgs(argv) {
  const event = {};
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--help' || arg === '-h') return { help: true };
    if (arg === '--quiet') {
      event.playSound = false;
      continue;
    }
    if (!['--pet', '--state', '--message'].includes(arg) || argv[i + 1] === undefined) {
      throw new Error(`无法识别参数：${arg}`);
    }
    const key = arg.slice(2);
    event[key] = argv[i + 1];
    i += 1;
  }
  return { event };
}

let parsed;
try {
  parsed = parseArgs(process.argv.slice(2));
} catch (error) {
  console.error(error.message);
  usage();
  process.exit(1);
}

if (parsed.help) {
  usage();
} else {
  const base = process.env.PET_COMPANION_URL || 'http://127.0.0.1:4173';
  try {
    const response = await fetch(`${base}/event`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(parsed.event),
      signal: AbortSignal.timeout(1000),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
    console.log(`已联动：${result.event.pet} / ${result.event.state}`);
  } catch (error) {
    console.error(`宠物联动不可用：${error.message}。请先运行 node companion/start.mjs`);
    process.exitCode = 1;
  }
}
