import { spawn } from 'node:child_process';
import { openSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = dirname(fileURLToPath(import.meta.url));
const port = Number(process.env.PORT) || 4173;
const url = `http://127.0.0.1:${port}`;

async function probe() {
  try {
    const response = await fetch(`${url}/health`, { signal: AbortSignal.timeout(600) });
    const data = await response.json();
    if (!response.ok || data.app !== 'pet-care-companion') return 'free';
    const page = await fetch(`${url}/index.html`, { signal: AbortSignal.timeout(600) });
    return page.ok && (page.headers.get('content-type') ?? '').includes('text/html') ? 'ready' : 'stale';
  } catch {
    return 'free';
  }
}

async function waitUntilReady() {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    if (await probe() === 'ready') return true;
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  return false;
}

function openBrowser() {
  if (process.env.PET_NO_OPEN === '1' || process.argv.includes('--no-open')) return;
  const command = process.platform === 'win32' ? 'cmd' : process.platform === 'darwin' ? 'open' : 'xdg-open';
  const args = process.platform === 'win32' ? ['/c', 'start', '', url] : [url];
  spawn(command, args, { detached: true, stdio: 'ignore', windowsHide: true }).unref();
}

// /health 只证明端口上有个同名服务，不证明它的页面文件还在（残留进程会 404 静态路由）
const status = await probe();
if (status === 'stale') {
  console.error(`端口 ${port} 上残留着一个页面打不开的宠物服务。请先结束占用 127.0.0.1:${port} 的 node 进程，再重新运行本命令。`);
  process.exit(1);
}

if (status === 'ready') {
  console.log(`宠物窗口已经在运行：${url}`);
} else {
  const logPath = join(tmpdir(), 'pet-care-companion.log');
  const log = openSync(logPath, 'a');
  const child = spawn(process.execPath, [join(ROOT, 'server.mjs')], {
    cwd: ROOT,
    detached: true,
    stdio: ['ignore', log, log],
    windowsHide: true,
    env: { ...process.env, PORT: String(port) },
  });
  child.unref();
  if (!await waitUntilReady()) {
    console.error(`宠物窗口启动失败，请查看日志：${logPath}`);
    process.exit(1);
  }
  console.log(`宠物窗口已启动：${url}`);
}

openBrowser();
