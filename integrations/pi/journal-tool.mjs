import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import path from "node:path";

const exec = promisify(execFile);
const cli = fileURLToPath(new URL("../../bin/journal", import.meta.url));
// Read-only verbs first; the two write verbs below touch different files on purpose.
const ACTIONS = ["tasks", "log-path", "log-ensure", "log-append", "journal-ensure", "journal-line"];

export function journalExtension({ root }) {
  if (!root || !path.isAbsolute(root)) throw new Error("Journal requires an absolute root.");
  return (pi) => pi.registerTool({
    name: "journal",
    label: "Journal and daily log",
    description: "Ricky's Markdown journal, read and written through the platform's journal command, which is the only authority for where a daily file lives. Never compose a vault path by hand. `tasks` lists task lines and modifies nothing. `log-ensure`/`log-append` write the dense internal daily log, which is your own space. `journal-ensure`/`journal-line` add to Ricky's own journal: one short summary line under its Notes section, sparingly, never a ghost-written entry. Tasks belong to Ricky in his own notes, never in your log.",
    parameters: { type: "object", required: ["action"], properties: {
      action: { type: "string", enum: ACTIONS },
      date: { type: "string", description: "YYYY-MM-DD for any daily-file action" },
      title: { type: "string", description: "Section title for log-append" },
      body: { type: "string", description: "Text for log-append, or the single line for journal-line" },
      tag: { type: "string", description: "tasks: filter by tag" },
      status: { type: "string", description: "tasks: open, done, all" },
      limit: { type: "integer", minimum: 1, maximum: 100 },
    } },
    async execute(_id, params, signal) {
      if (!ACTIONS.includes(params.action)) throw new Error("Unsupported journal action.");
      const args = [cli, "--root", root, params.action];
      if (params.action === "tasks") {
        if (params.tag) args.push("--tag", params.tag);
        if (params.status) args.push("--status", params.status);
        args.push("--limit", String(params.limit ?? 20), "--json");
      } else {
        if (!params.date) throw new Error("A daily journal action needs an explicit date.");
        args.push(params.date);
        if (params.action === "log-append") {
          if (!params.title || !params.body) throw new Error("log-append needs a title and a body.");
          args.push("--title", params.title, "--body", params.body);
        }
        if (params.action === "journal-line") {
          if (!params.body) throw new Error("journal-line needs the single line to add.");
          args.push("--line", params.body);
        }
      }
      try {
        const { stdout } = await exec("python3", args, { signal, timeout: 30000, maxBuffer: 1024 * 1024 });
        return { content: [{ type: "text", text: stdout || "done" }], details: { journal: true } };
      } catch (error) {
        throw new Error(`Journal action failed: ${String(error.message ?? error).slice(0, 200)}`);
      }
    },
  });
}
