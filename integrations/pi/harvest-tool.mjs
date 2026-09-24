import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

const exec = promisify(execFile);
const cli = fileURLToPath(new URL("../../bin/harvest", import.meta.url));
const READ = ["projects", "hours", "list"];
const WRITE = ["create", "update", "delete"];
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const ID = /^\d{1,18}$/;

/** Build the command line for one action. Pure and exported so it is tested without
 *  a Keychain, a network, or any chance of touching Ricky's real time entries. */
export function harvestArgs(params) {
  const { action } = params;
  if (![...READ, ...WRITE].includes(action)) throw new Error("Unsupported Harvest action.");
  const args = [action];
  const date = (value, label) => {
    if (!DATE.test(value ?? "")) throw new Error(`${label} must be YYYY-MM-DD.`);
    return value;
  };
  const entryId = (value) => {
    if (!ID.test(value ?? "")) throw new Error("An entry id is the number shown by list.");
    return value;
  };
  if (action === "hours" || action === "list") {
    if (params.from) args.push(date(params.from, "from"));
    if (params.to) { if (!params.from) throw new Error("Give from before to."); args.push(date(params.to, "to")); }
  } else if (action === "create") {
    if (typeof params.hours !== "number" || params.hours <= 0) throw new Error("create needs hours above zero.");
    if (!ID.test(params.project_id ?? "") || !ID.test(params.task_id ?? "")) {
      throw new Error("create needs a project_id and task_id from projects.");
    }
    args.push(date(params.date, "date"), String(params.hours), params.project_id, params.task_id, params.notes ?? "");
  } else if (action === "update") {
    args.push(entryId(params.id));
    if (typeof params.hours === "number") args.push("--hours", String(params.hours));
    if (params.notes) args.push("--notes", params.notes);
    if (args.length === 2) throw new Error("update needs hours or notes to change.");
  } else if (action === "delete") {
    args.push(entryId(params.id));
  }
  return args;
}

export function harvestExtension({ agent }) {
  // Hours and invoices are the personal role's job; no other role bills.
  if (agent !== "morty") throw new Error("Harvest belongs to the personal role.");
  return (pi) => pi.registerTool({
    name: "harvest",
    label: "Harvest time tracking",
    description:
      "Ricky's Harvest account, through the platform's harvest command. The credential stays in the macOS Keychain and is read by the command, never by you.\n" +
      "- projects: the projects and tasks he is assigned, with their ids. Use these exact project names when reconciling journal work entries.\n" +
      "- hours: totals by day and by project for a date range, this month by default.\n" +
      "- list: individual entries with their ids.\n" +
      "- create / update / delete: change his time entries. These are his records and his billing. Confirm the exact date, hours, project and notes with him in conversation first, and say what you are about to do before you do it. Never infer an entry from a journal line on your own.",
    parameters: { type: "object", required: ["action"], properties: {
      action: { type: "string", enum: [...READ, ...WRITE] },
      from: { type: "string", description: "hours/list: start date YYYY-MM-DD" },
      to: { type: "string", description: "hours/list: end date YYYY-MM-DD" },
      date: { type: "string", description: "create: the date worked, YYYY-MM-DD" },
      hours: { type: "number", minimum: 0, maximum: 24 },
      project_id: { type: "string", description: "create: from projects" },
      task_id: { type: "string", description: "create: from projects" },
      notes: { type: "string" },
      id: { type: "string", description: "update/delete: the entry id from list" },
    } },
    async execute(_id, params, signal) {
      const args = harvestArgs(params);
      try {
        const { stdout } = await exec(cli, args, { signal, timeout: 30000, maxBuffer: 1024 * 1024 });
        return { content: [{ type: "text", text: stdout || "done" }],
                 details: { harvest: true, wrote: WRITE.includes(action) } };
      } catch (error) {
        throw new Error(`Harvest ${action} failed: ${String(error.message ?? error).slice(0, 200)}`);
      }
    },
  });
}
