/** Account-bound role terminal entry. Started only by ai-role through the lock boundary. */
import path from 'node:path';
import { ModelRuntime } from '@earendil-works/pi-coding-agent';
import { runRoleTerminal } from './role-terminal.mjs';

function fail(message) { process.stderr.write(`role-launch: ${message}\n`); process.exit(2); }

const raw = process.env.DEV_PLATFORM_ROLE_LAUNCH;
if (!raw) fail('start Pi roles through ai-role');
let launch;
try { launch = JSON.parse(raw); } catch { fail('unreadable launch plan'); }
if (launch?.version !== 1 || !launch.conversation?.id) fail('unsupported launch plan');
for (const key of ['conversationHome', 'platformRoot', 'agentDir', 'identityFile']) {
  if (typeof launch[key] !== 'string' || !path.isAbsolute(launch[key])) fail(`${key} must be an absolute path`);
}
if (process.env.PI_CODING_AGENT_DIR !== launch.agentDir) fail('Pi profile directory differs from the launch plan');
if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/.test(launch.modelId ?? '')) fail('invalid model id');
if (!['openai-codex', 'anthropic'].includes(launch.provider)) fail('unsupported provider');
const offline = launch.offline === true;

try {
  // Same construction as Pi's own interactive entry; offline mode only skips network refresh.
  const modelRuntime = await ModelRuntime.create({
    authPath: path.join(launch.agentDir, 'auth.json'),
    modelsPath: path.join(launch.agentDir, 'models.json'),
    signal: AbortSignal.timeout(15_000),
    ...(offline ? { refreshOnCreate: false, allowModelNetwork: false } : {}),
  });
  const model = modelRuntime.getModel(launch.provider, launch.modelId);
  if (!model) {
    const known = modelRuntime.getModels(launch.provider).map(m => m.id).join(', ');
    fail(`model ${launch.provider}/${launch.modelId} unavailable; known: ${known}`);
  }
  if (!offline && !modelRuntime.hasConfiguredAuth(launch.provider)) {
    fail(`no Pi sign-in for ${launch.provider} in this profile; run Pi /login in the profile first`);
  }
  await runRoleTerminal({
    conversation: launch.conversation, conversationHome: launch.conversationHome,
    platformRoot: launch.platformRoot, agentDir: launch.agentDir, identityFile: launch.identityFile,
    historyArchive: launch.historyArchive || undefined, memoryState: launch.memoryState || undefined, journalRoot: launch.journalRoot || undefined,
    modelRuntime, model,
    accountRef: launch.accountRef, resumeFile: launch.resumeFile || undefined,
  });
} catch (error) {
  fail(error instanceof Error ? error.message : String(error));
}
