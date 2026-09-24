/** Offline checks for the Harvest tool. Builds command lines and refuses bad input.
 *  Never runs the real command, so Ricky's time entries are never touched. */
import assert from 'node:assert/strict';
import { harvestArgs, harvestExtension } from './harvest-tool.mjs';

assert.deepEqual(harvestArgs({action:'projects'}), ['projects']);
assert.deepEqual(harvestArgs({action:'hours'}), ['hours']);
assert.deepEqual(harvestArgs({action:'hours', from:'2026-09-01', to:'2026-09-24'}),
                 ['hours','2026-09-01','2026-09-24']);
assert.deepEqual(harvestArgs({action:'list', from:'2026-09-01'}), ['list','2026-09-01']);
assert.deepEqual(
  harvestArgs({action:'create', date:'2026-09-24', hours:1.5, project_id:'46567554', task_id:'25399411', notes:'webhook fix'}),
  ['create','2026-09-24','1.5','46567554','25399411','webhook fix']);
assert.deepEqual(harvestArgs({action:'update', id:'123', hours:2}), ['update','123','--hours','2']);
assert.deepEqual(harvestArgs({action:'delete', id:'123'}), ['delete','123']);

// Anything malformed is refused before a process starts.
const refused = [
  {action:'sync'},
  {action:'hours', from:'yesterday'},
  {action:'hours', to:'2026-09-24'},
  {action:'create', date:'2026-09-24', hours:0, project_id:'1', task_id:'2'},
  {action:'create', date:'24-09-2026', hours:1, project_id:'1', task_id:'2'},
  {action:'create', date:'2026-09-24', hours:1, project_id:'notanid', task_id:'2'},
  {action:'update', id:'123'},
  {action:'update', id:'abc', hours:1},
  {action:'delete', id:'; rm -rf ~'},
];
for (const params of refused) {
  assert.throws(() => harvestArgs(params), `should have refused ${JSON.stringify(params)}`);
}

// Only the personal role bills.
for (const agent of ['iztac','neo',undefined]) {
  assert.throws(() => harvestExtension({agent}), /personal role/);
}
let tool;
harvestExtension({agent:'morty'})({registerTool: (t) => { tool = t; }});
assert.equal(tool.name, 'harvest');
assert.deepEqual(tool.parameters.properties.action.enum,
                 ['projects','hours','list','create','update','delete']);
// The description must tell the role to confirm before changing his records.
assert.match(tool.description, /Confirm the exact date, hours, project and notes with him/);
assert.match(tool.description, /credential stays in the macOS Keychain/);

console.log(JSON.stringify({passed:true, checks:[
  'command lines for every read and write action',
  'malformed dates, ids, hours and unknown actions refused before execution',
  'only the personal role receives the tool',
  'writes carry an explicit confirm-first instruction'],
  scope:'Pure argument building; no Keychain read, no network, no time entry touched'}, null, 2));
