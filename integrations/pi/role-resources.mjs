/** Explicit role resources for Pi; no auth, dispatch or model calls. */
import fs from 'node:fs';
import path from 'node:path';
import { DefaultResourceLoader, SettingsManager } from '@earendil-works/pi-coding-agent';
import { historyExtension } from './history-tool.mjs';
import { memoryExtension } from './memory-tool.mjs';
import { journalExtension } from './journal-tool.mjs';

export async function loadRoleResources({ conversation, conversationHome, platformRoot, agentDir, identityFile, historyArchive, memoryState, journalRoot, extensionFactories = [] }) {
  const { agent, scope, binding } = conversation;
  if (!['morty','iztac','neo'].includes(agent)) throw new Error('Unknown agent role');
  const project = ['project','formation'].includes(scope?.kind);
  if (agent === 'morty' && scope?.kind !== 'personal') throw new Error('Morty requires personal scope');
  if (agent === 'iztac' && !project) throw new Error('Iztac requires project scope');
  if (agent === 'neo' && !project && scope?.kind !== 'system') throw new Error('Neo requires system or project scope');
  if (!path.isAbsolute(conversationHome) || !path.isAbsolute(platformRoot) || !path.isAbsolute(agentDir) || !path.isAbsolute(identityFile)) {
    throw new Error('Role resource paths must be absolute');
  }
  if (memoryState !== undefined && !path.isAbsolute(memoryState)) throw new Error('Memory state root must be absolute');
  if (journalRoot !== undefined && !path.isAbsolute(journalRoot)) throw new Error('Journal root must be absolute');
  // Every role reads the journal; what each may WRITE is decided inside the tool.
  // Personal/system sessions execute in their neutral conversation workspace.
  // Invocation cwd never participates in resource selection.
  let cwd;
  if (project) {
    if (!binding?.workspace || !path.isAbsolute(binding.workspace)) throw new Error('Missing explicit workspace');
    cwd = fs.realpathSync(binding.workspace);
    if (!fs.statSync(cwd).isDirectory()) throw new Error('Workspace is not a directory');
  } else {
    cwd = path.join(conversationHome, 'workspace');
    if (fs.existsSync(cwd) && fs.lstatSync(cwd).isSymbolicLink()) throw new Error('Neutral workspace cannot be a symlink');
    fs.mkdirSync(cwd,{recursive:true,mode:0o700});
  }
  const identity = {path:identityFile,content:fs.readFileSync(identityFile,'utf8')};
  // Startup guidance must be in context, not merely available for skill discovery.
  const entryPath = path.join(platformRoot,'skills/session-entry/SKILL.md');
  const entry = {path:entryPath,content:fs.readFileSync(entryPath,'utf8')};
  // The role's own memory index rides in context so it starts oriented; the daily
  // corpus and the inherited records stay behind the agent_memory tool.
  let memory = null;
  if (memoryState) {
    const indexPath = path.join(memoryState, agent, 'memory', 'MEMORY.md');
    if (fs.existsSync(indexPath) && !fs.lstatSync(indexPath).isSymbolicLink()) {
      memory = {path:indexPath, content:fs.readFileSync(indexPath,'utf8')};
    }
  }
  const settingsManager = SettingsManager.inMemory();
  const loader = new DefaultResourceLoader({
    cwd, agentDir, settingsManager,
    noExtensions:true, noSkills:true, noPromptTemplates:true, noThemes:true,
    additionalExtensionPaths:[path.join(platformRoot,'integrations/pi/perplexity.ts')],
    extensionFactories:[...(historyArchive ? [historyExtension({archive:historyArchive,agent})] : []),
      ...(memoryState ? [memoryExtension({agent, state:memoryState})] : []),
      ...(journalRoot ? [journalExtension({root:journalRoot, agent})] : []), ...extensionFactories],
    noContextFiles:!project,
    additionalSkillPaths:agent==='iztac'?[path.join(platformRoot,'agents/iztac/skills/iztac-engineering')]:[],
    agentsFilesOverride:base=>({agentsFiles:[entry,identity,...(memory?[memory]:[]),...(project?base.agentsFiles:[])]}),
  });
  await loader.reload();
  if (loader.getExtensions().errors.length) throw new Error('Role extension loading failed');
  const errors = loader.getSkills().diagnostics.filter(d=>d.type==='error');
  if (errors.length) throw new Error('Role skill loading failed');
  return {cwd,loader,settingsManager,memoryIndex:memory?.path ?? null,sessionDirectory:path.join(conversationHome,'native/pi')};
}
