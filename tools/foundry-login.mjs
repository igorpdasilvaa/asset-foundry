#!/usr/bin/env node
// Login no Foundry num Chrome dedicado (perfil próprio + porta de debug local).
// Rode VOCÊ no seu terminal: a senha é lida aqui (prompt oculto) e nunca é
// gravada em arquivo, em log nem passada a outra ferramenta.
//
//   FOUNDRY_URL=https://meu-foundry.exemplo FOUNDRY_USER="Igor" node tools/foundry-login.mjs
//
// Opcionais: FOUNDRY_PORT (9222), FOUNDRY_PROFILE (~/.config/foundry-chrome),
// FOUNDRY_CHROME (google-chrome). FOUNDRY_PASSWORD existe para automação sua,
// mas o prompt oculto é o caminho recomendado (não deixa a senha no histórico).
import { execFileSync, spawn } from "node:child_process";
import { chmodSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { createInterface } from "node:readline";

// Uso salvo (digita a senha uma vez, nunca mais):
//   node tools/foundry-login.mjs --save     (pede URL, usuário e senha)
//   node tools/foundry-login.mjs            (usa o que foi salvo)
// A senha fica no chaveiro do sistema (secret-tool) se existir; senão em
// <perfil>/login.json com permissão 600. Nunca dentro do repositório.
const PORT = Number(process.env.FOUNDRY_PORT ?? 9222);
const PROFILE = process.env.FOUNDRY_PROFILE ?? join(homedir(), ".config", "foundry-chrome");
const CHROME = process.env.FOUNDRY_CHROME ?? "google-chrome";
const DEBUG = `http://127.0.0.1:${PORT}`;
const CONFIG = join(PROFILE, "login.json");
const SAVE = process.argv.includes("--save");

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const die = (msg) => { console.error(`erro: ${msg}`); process.exit(1); };

const readConfig = () => { try { return JSON.parse(readFileSync(CONFIG, "utf8")); } catch { return {}; } };
const keyringArgs = (url, user) => ["service", "foundry-login", "url", url, "user", user];
function keyringGet(url, user) {
  try { return execFileSync("secret-tool", ["lookup", ...keyringArgs(url, user)], { stdio: ["ignore", "pipe", "ignore"] }).toString(); }
  catch { return null; }
}
function keyringSet(url, user, password) {
  try {
    execFileSync("secret-tool", ["store", `--label=Foundry ${user}@${url}`, ...keyringArgs(url, user)], { input: password, stdio: ["pipe", "ignore", "ignore"] });
    return true;
  } catch { return false; }
}
function saveLogin(url, user, password) {
  mkdirSync(PROFILE, { recursive: true, mode: 0o700 });
  const inKeyring = keyringSet(url, user, password);
  writeFileSync(CONFIG, JSON.stringify(inKeyring ? { url, user } : { url, user, password }), { mode: 0o600 });
  chmodSync(CONFIG, 0o600);
  console.log(inKeyring ? "Senha salva no chaveiro do sistema." : `Senha salva em ${CONFIG} (permissão 600).`);
}

function askHidden(prompt) {
  return new Promise((resolve) => {
    const rl = createInterface({ input: process.stdin, output: process.stdout, terminal: true });
    rl._writeToOutput = (s) => { if (s.includes(prompt)) process.stdout.write(s); };
    rl.question(prompt, (answer) => { rl.close(); process.stdout.write("\n"); resolve(answer); });
  });
}

async function debugUp() {
  try { return (await fetch(`${DEBUG}/json/version`)).ok; } catch { return false; }
}

async function ensureChrome() {
  if (await debugUp()) return;
  spawn(CHROME, [
    `--remote-debugging-port=${PORT}`, "--remote-debugging-address=127.0.0.1",
    `--user-data-dir=${PROFILE}`, "--no-first-run", "--no-default-browser-check", "about:blank",
  ], { detached: true, stdio: "ignore" }).unref();
  for (let i = 0; i < 40; i++) { if (await debugUp()) return; await sleep(250); }
  die(`Chrome não abriu a porta de debug ${PORT}`);
}

async function openTarget(url) {
  const r = await fetch(`${DEBUG}/json/new?${encodeURIComponent(url)}`, { method: "PUT" });
  if (!r.ok) die(`não consegui abrir a aba (${r.status})`);
  return (await r.json()).webSocketDebuggerUrl;
}

function cdp(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  const ready = new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error("falha no WebSocket do CDP")); });
  ws.onmessage = (ev) => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  };
  const send = (method, params = {}) => new Promise((res) => {
    pending.set(++id, res);
    ws.send(JSON.stringify({ id, method, params }));
  });
  const evaluate = async (expression) => {
    const m = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    return m.result?.result?.value;
  };
  return { ready, evaluate, close: () => ws.close() };
}

async function waitFor(evaluate, expression, tries = 60) {
  for (let i = 0; i < tries; i++) { if (await evaluate(expression)) return true; await sleep(500); }
  return false;
}

const saved = readConfig();
const ask = (label) => new Promise((r) => { const rl = createInterface({ input: process.stdin, output: process.stdout }); rl.question(label, (a) => { rl.close(); r(a.trim()); }); });
const URL_BASE = (process.env.FOUNDRY_URL ?? (SAVE ? await ask(`URL do Foundry [${saved.url ?? ""}]: `) || saved.url : saved.url) ?? "").replace(/\/+$/, "");
const USER = process.env.FOUNDRY_USER ?? (SAVE ? await ask(`Usuário [${saved.user ?? ""}]: `) || saved.user : saved.user) ?? "";
if (!URL_BASE || !USER) die("nada salvo ainda: rode com --save (ou defina FOUNDRY_URL e FOUNDRY_USER)");

let password = process.env.FOUNDRY_PASSWORD;
if (password === undefined && !SAVE) password = keyringGet(URL_BASE, USER) ?? saved.password;
if (password === undefined) {
  password = await askHidden(`Senha de "${USER}" (Enter se não houver): `);
  if (SAVE) saveLogin(URL_BASE, USER, password);
}

await ensureChrome();
const page = cdp(await openTarget(`${URL_BASE}/join`));
await page.ready;

if (!(await waitFor(page.evaluate, `!!document.querySelector('select[name=userid]')`))) {
  const onGame = await page.evaluate(`location.pathname`);
  if (onGame === "/game") { console.log("Já estava logado (sessão ativa)."); page.close(); process.exit(0); }
  die("tela de login não apareceu (URL errada, mundo não iniciado ou Foundry fora do ar)");
}

// Dados entram via JSON.stringify: sem concatenação cega no JS da página.
const filled = await page.evaluate(`(() => {
  const sel = document.querySelector('select[name=userid]');
  const opt = [...sel.options].find((o) => o.textContent.trim() === ${JSON.stringify(USER)});
  if (!opt) return "usuario";
  sel.value = opt.value; sel.dispatchEvent(new Event("change", { bubbles: true }));
  const pw = document.querySelector('input[name=password]');
  if (pw) { pw.value = ${JSON.stringify(password)}; pw.dispatchEvent(new Event("input", { bubbles: true })); }
  document.querySelector('button[name=join]').click();
  return "ok";
})()`);
if (filled === "usuario") die(`usuário "${USER}" não existe na lista do Foundry`);

const logged = await waitFor(page.evaluate, `location.pathname === "/game"`, 40);
page.close();
if (!logged) die("não entrou (senha errada ou usuário bloqueado?)");
console.log(`Logado em ${URL_BASE}. Perfil: ${PROFILE} (porta de debug ${PORT}, só localhost).`);
