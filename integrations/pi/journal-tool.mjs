import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import path from "node:path";

const exec = promisify(execFile);
const cli = fileURLToPath(new URL("../../bin/journal", import.meta.url));
const ROLE = { morty: "Morty", iztac: "Iztac", neo: "Neo" };
// What each role may do, by construction rather than by instruction. Reading is
// shared; the personal role keeps custody of Ricky's own journal and his tasks.
const ALLOWED = {
  morty: ["tasks", "entries", "work", "task", "log-ensure", "log-append", "journal-line", "log-path"],
  iztac: ["tasks", "entries", "work"],
  neo: ["tasks", "entries", "work"],
};

export function journalExtension({ root, agent }) {
  if (!root || !path.isAbsolute(root)) throw new Error("Journal requires an absolute root.");
  const role = ROLE[agent];
  const allowed = ALLOWED[agent];
  if (!role || !allowed) throw new Error("Journal requires a known agent role.");
  const personal = agent === "morty";
  return (pi) => pi.registerTool({
    name: "journal",
    label: "Journal",
    description:
      `Ricky's Markdown journal, through the platform's journal command, which is the only authority for where a daily file lives. You never name a path or a date.\n` +
      `- tasks: list his task lines. Reads only.\n` +
      `- entries: read a day's structured work entries, each with its role, project and minutes. An entry with no project cannot be billed.\n` +
      `- work: add one entry for work you did, to today's note. Always give a project when the work belongs to one, and minutes when you know them, because Morty reconciles hours and invoices from these.\n` +
      (personal
        ? `- task: create one task line for Ricky.\n- log-ensure / log-append: your own dense daily log.\n- journal-line: one summary line in Ricky's journal. His space: write sparingly and never in his voice.\n`
        : `Writing his journal, his tasks and the personal daily log is Morty's, not yours. Durable reference belongs in your memory, not here.\n`),
    parameters: { type: "object", required: ["action"], properties: {
      action: { type: "string", enum: allowed },
      summary: { type: "string", description: "work: what you did, one sentence" },
      project: { type: "string", description: "work: the project this belongs to, so it can be billed" },
      minutes: { type: "integer", minimum: 1, maximum: 1440, description: "work: time spent" },
      date: { type: "string", description: "entries: YYYY-MM-DD; defaults to today" },
      text: { type: "string", description: "task: the task description" },
      tag: { type: "string" }, due: { type: "string" }, scheduled: { type: "string" },
      priority: { type: "string", enum: ["highest", "high", "medium", "low"] },
      title: { type: "string", description: "log-append: section title" },
      body: { type: "string", description: "log-append: section body, or journal-line: the line" },
    } },
    async execute(_id, params, signal) {
      if (!allowed.includes(params.action)) {
        throw new Error(`${params.action} is not available to ${role}.`);
      }
      const args = [cli, "--root", root, params.action];
      if (params.action === "tasks") args.push("--limit", "20", "--json");
      else if (params.action === "entries") { if (params.date) args.push(params.date); }
      else if (params.action === "work") {
        if (!params.summary) throw new Error("A work entry needs a summary.");
        // The role is fixed by the launch, never chosen by the caller.
        args.push("--role", role, "--summary", params.summary);
        if (params.project) args.push("--project", params.project);
        if (params.minutes) args.push("--minutes", String(params.minutes));
      } else if (params.action === "task") {
        if (!params.text) throw new Error("A task needs a description.");
        args.push("--text", params.text);
        for (const [flag, value] of [["--tag", params.tag], ["--due", params.due],
                                     ["--scheduled", params.scheduled], ["--priority", params.priority]]) {
          if (value) args.push(flag, value);
        }
      } else if (params.action === "log-append") {
        if (!params.title || !params.body) throw new Error("log-append needs a title and a body.");
        args.push("--title", params.title, "--body", params.body);
      } else if (params.action === "journal-line") {
        if (!params.body) throw new Error("journal-line needs the single line to add.");
        args.push("--line", params.body);
      }
      try {
        const { stdout } = await exec("python3", args, { signal, timeout: 30000, maxBuffer: 1024 * 1024 });
        return { content: [{ type: "text", text: stdout || "done" }], details: { journal: true, role } };
      } catch (error) {
        throw new Error(`Journal action failed: ${String(error.message ?? error).slice(0, 200)}`);
      }
    },
  });
}
