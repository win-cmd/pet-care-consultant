import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { DEFAULT_EVENT, normalizeEvent } from './protocol.mjs';

const ROOT = dirname(fileURLToPath(import.meta.url));
const MAX_BODY = 8192;
const STATIC_FILES = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/index.html', ['index.html', 'text/html; charset=utf-8']],
  ['/styles.css', ['styles.css', 'text/css; charset=utf-8']],
  ['/app.js', ['app.js', 'text/javascript; charset=utf-8']],
  ['/protocol.mjs', ['protocol.mjs', 'text/javascript; charset=utf-8']],
]);

function sendJson(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(body),
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
  });
  res.end(body);
}

function isLocalRequest(req) {
  const host = req.headers.host ?? '';
  if (!/^(127\.0\.0\.1|localhost)(:\d+)?$/i.test(host)) return false;
  const origin = req.headers.origin;
  if (!origin) return true;
  try {
    return ['127.0.0.1', 'localhost'].includes(new URL(origin).hostname);
  } catch {
    return false;
  }
}

async function readJson(req) {
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_BODY) {
      const error = new Error('请求体过大');
      error.status = 413;
      throw error;
    }
    chunks.push(chunk);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
  } catch {
    const error = new Error('JSON 格式不正确');
    error.status = 400;
    throw error;
  }
}

export function createCompanionServer() {
  let current = { ...DEFAULT_EVENT, eventId: 0, sentAt: Date.now() };
  const clients = new Set();

  function broadcast() {
    const payload = `event: pet\ndata: ${JSON.stringify(current)}\n\n`;
    for (const client of clients) client.write(payload);
  }

  const server = http.createServer(async (req, res) => {
    if (!isLocalRequest(req)) {
      sendJson(res, 403, { ok: false, error: '仅允许本机访问' });
      return;
    }

    const url = new URL(req.url, 'http://127.0.0.1');
    if (req.method === 'GET' && url.pathname === '/health') {
      sendJson(res, 200, { ok: true, app: 'pet-care-companion', eventId: current.eventId });
      return;
    }

    if (req.method === 'GET' && url.pathname === '/events') {
      res.writeHead(200, {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
        'X-Accel-Buffering': 'no',
      });
      res.write('retry: 1000\n\n');
      res.write(`event: pet\ndata: ${JSON.stringify(current)}\n\n`);
      clients.add(res);
      req.on('close', () => clients.delete(res));
      return;
    }

    if (req.method === 'POST' && url.pathname === '/event') {
      if (!/^application\/json\b/i.test(req.headers['content-type'] ?? '')) {
        sendJson(res, 415, { ok: false, error: 'Content-Type 必须是 application/json' });
        return;
      }
      try {
        const input = await readJson(req);
        const normalized = normalizeEvent(input, current);
        current = { ...normalized, eventId: current.eventId + 1, sentAt: Date.now() };
        broadcast();
        sendJson(res, 200, { ok: true, event: current });
      } catch (error) {
        sendJson(res, error.status ?? 400, { ok: false, error: error.message });
      }
      return;
    }

    if (req.method === 'GET' && STATIC_FILES.has(url.pathname)) {
      const [file, contentType] = STATIC_FILES.get(url.pathname);
      try {
        const body = await readFile(join(ROOT, file));
        res.writeHead(200, {
          'Content-Type': contentType,
          'Cache-Control': 'no-cache',
          'X-Content-Type-Options': 'nosniff',
          'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; media-src 'none'; object-src 'none'; base-uri 'none'",
        });
        res.end(body);
      } catch {
        sendJson(res, 404, { ok: false, error: '文件不存在' });
      }
      return;
    }

    sendJson(res, 404, { ok: false, error: '路径不存在' });
  });

  const heartbeat = setInterval(() => {
    for (const client of clients) client.write(': keepalive\n\n');
  }, 15000);
  heartbeat.unref();
  server.on('close', () => {
    clearInterval(heartbeat);
    for (const client of clients) client.end();
    clients.clear();
  });
  return server;
}

export function listen(port = Number(process.env.PORT) || 4173) {
  const server = createCompanionServer();
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

if (process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  const port = Number(process.env.PORT) || 4173;
  listen(port).then(() => {
    console.log(`宠物窗口已启动：http://127.0.0.1:${port}`);
  }).catch((error) => {
    console.error(`启动失败：${error.message}`);
    process.exitCode = 1;
  });
}
