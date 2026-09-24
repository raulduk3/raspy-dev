/** Run Pi's native terminal under the account launcher's conversation lock. */
import fs from 'node:fs';
import path from 'node:path';
import { InteractiveMode, initTheme } from '@earendil-works/pi-coding-agent';
import { createRoleRuntime } from './role-runtime.mjs';

export async function runRoleTerminal(options) {
  if (!process.stdin.isTTY || !process.stdout.isTTY) throw new Error('Pi requires an interactive terminal');
  const descriptor=process.env.DEV_PLATFORM_PI_LOCK_FD;
  if (!descriptor || !/^\d+$/.test(descriptor)) throw new Error('Start Pi through the conversation launch boundary');
  const held=fs.fstatSync(Number(descriptor));
  const expected=fs.statSync(path.join(options.conversationHome,'.pi-writer.lock'));
  if (held.dev!==expected.dev || held.ino!==expected.ino) throw new Error('Writer lock belongs to a different conversation');
  // Keep the descriptor open. The launching process acquired flock before exec.
  // This identity check is a wiring check, not protection from same-user code.
  const runtime=await createRoleRuntime(options);
  try {
    initTheme(runtime.services.settingsManager.getTheme(),true);
    await new InteractiveMode(runtime,{verbose:true}).run();
  } finally {await runtime.dispose();}
}
