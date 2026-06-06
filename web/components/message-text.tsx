import { AGENTS, isAgentId } from "@/lib/agents";

/** Renders message text, highlighting @agent mentions as colored chips. */
export function MessageText({ text }: { text: string }) {
  const parts = text.split(/(@[a-z_]+)/gi);
  return (
    <span className="whitespace-pre-wrap break-words">
      {parts.map((part, i) => {
        if (part.startsWith("@")) {
          const handle = part.slice(1).toLowerCase();
          if (isAgentId(handle)) {
            return (
              <span
                key={i}
                className="rounded bg-blue-500/15 px-1 font-medium text-blue-300"
              >
                @{AGENTS[handle].name}
              </span>
            );
          }
        }
        return <span key={i}>{part}</span>;
      })}
    </span>
  );
}
