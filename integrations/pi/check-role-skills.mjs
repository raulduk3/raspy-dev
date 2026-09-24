import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { DefaultResourceLoader, SettingsManager } from '@earendil-works/pi-coding-agent';

const repository = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const skill = path.join(repository, 'agents/iztac/skills/iztac-engineering');
const root = fs.mkdtempSync(path.join(os.tmpdir(), 'pi-role-skills-'));
const results = [];
try {
  // Fixtures deliberately contain an unrelated discoverable skill and repository context.
  const inherited = path.join(root, '.pi/skills/unwanted');
  fs.mkdirSync(inherited, {recursive:true});
  fs.writeFileSync(path.join(inherited,'SKILL.md'), '---\nname: unwanted\ndescription: Unrelated fixture\n---\nDo not inherit.\n');
  fs.writeFileSync(path.join(root,'AGENTS.md'),'UNRELATED_REPOSITORY_CONTEXT');
  for (const agent of ['morty','iztac','neo']) {
    const loader = new DefaultResourceLoader({cwd:root, agentDir:path.join(root,'config'),
      settingsManager:SettingsManager.inMemory(), noExtensions:true, noSkills:true,
      noContextFiles:true, noPromptTemplates:true, noThemes:true,
      additionalSkillPaths:agent==='iztac'?[skill]:[]});
    await loader.reload();
    const loaded = loader.getSkills();
    assert.deepEqual(loaded.diagnostics, []);
    assert.deepEqual(loaded.skills.map(s=>s.name),agent==='iztac'?['iztac-engineering']:[]);
    assert.deepEqual(loader.getAgentsFiles().agentsFiles,[]);
    results.push({agent,skills:loaded.skills.map(s=>s.name)});
  }
  const body = fs.readFileSync(path.join(skill,'SKILL.md'),'utf8');
  const links = [...body.matchAll(/\]\(((?:references\/|\.\.\/\.\.\/\.\.\/\.\.\/skills\/principle-)[^)]+)\)/g)].map(m=>m[1]);
  assert.equal(links.filter(p=>p.includes('/skills/principle-')).length,23);
  for (const relative of links) assert(fs.statSync(path.join(skill,relative)).isFile(),relative);
  console.log(JSON.stringify({passed:true,results,referenceFiles:links.length,
    scope:'Actual Pi resource loader with isolated fixtures; no inference, authentication, or production launcher tested.'},null,2));
} finally {
  fs.rmSync(root,{recursive:true,force:true});
}
