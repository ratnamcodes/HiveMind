"use client";

import { useRef, useState, type ChangeEvent, type KeyboardEvent } from "react";
import { SendHorizontal } from "lucide-react";
import { AGENT_IDS, AGENTS, type AgentMeta } from "@/lib/agents";
import { useWarRoom } from "@/lib/store";
import { cn } from "@/lib/utils";
import { AgentAvatar } from "./agent-avatar";

export function Composer({
  channelId,
  channelName,
}: {
  channelId: string;
  channelName: string;
}) {
  const sendMessage = useWarRoom((s) => s.sendMessage);
  const [value, setValue] = useState("");
  const [query, setQuery] = useState<string | null>(null);
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLTextAreaElement>(null);

  const suggestions: AgentMeta[] =
    query !== null
      ? AGENT_IDS.map((id) => AGENTS[id]).filter(
          (a) =>
            a.id.toLowerCase().includes(query) ||
            a.name.toLowerCase().includes(query),
        )
      : [];

  function autoGrow() {
    const ta = ref.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, 160)}px`;
  }

  function onChange(e: ChangeEvent<HTMLTextAreaElement>) {
    const v = e.target.value;
    setValue(v);
    const caret = e.target.selectionStart ?? v.length;
    const m = /(?:^|\s)@([a-z_]*)$/i.exec(v.slice(0, caret));
    setQuery(m ? m[1].toLowerCase() : null);
    setActive(0);
    autoGrow();
  }

  function applyMention(agent: AgentMeta) {
    const ta = ref.current;
    const caret = ta?.selectionStart ?? value.length;
    const upto = value.slice(0, caret).replace(/@([a-z_]*)$/i, `@${agent.id} `);
    const next = upto + value.slice(caret);
    setValue(next);
    setQuery(null);
    requestAnimationFrame(() => {
      ta?.focus();
      ta?.setSelectionRange(upto.length, upto.length);
      autoGrow();
    });
  }

  function submit() {
    const text = value.trim();
    if (!text) return;
    sendMessage(channelId, text);
    setValue("");
    setQuery(null);
    requestAnimationFrame(autoGrow);
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (query !== null && suggestions.length) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive((i) => (i + 1) % suggestions.length);
        return;
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive((i) => (i - 1 + suggestions.length) % suggestions.length);
        return;
      }
      if (e.key === "Enter" || e.key === "Tab") {
        e.preventDefault();
        applyMention(suggestions[active]);
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        setQuery(null);
        return;
      }
    }
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  }

  return (
    <div className="relative px-4 pb-5 pt-1">
      {query !== null && suggestions.length > 0 && (
        <div className="absolute bottom-full left-4 right-4 mb-2 overflow-hidden rounded-lg border bg-popover shadow-xl">
          <div className="border-b px-3 py-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            Agents
          </div>
          {suggestions.map((a, i) => (
            <button
              key={a.id}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                applyMention(a);
              }}
              onMouseEnter={() => setActive(i)}
              className={cn(
                "flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm",
                i === active ? "bg-accent" : "hover:bg-accent/50",
              )}
            >
              <AgentAvatar agent={a.id} size="sm" />
              <span className="font-medium text-foreground">{a.name}</span>
              <span className="ml-auto text-xs text-muted-foreground">
                {a.partner}
              </span>
            </button>
          ))}
        </div>
      )}

      <div className="flex items-end gap-2 rounded-xl border bg-card px-3 py-2.5 transition-colors focus-within:border-ring">
        <textarea
          ref={ref}
          value={value}
          onChange={onChange}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder={`Message #${channelName}`}
          className="max-h-40 flex-1 resize-none bg-transparent text-sm leading-relaxed text-foreground outline-none placeholder:text-muted-foreground"
        />
        <button
          type="button"
          onClick={submit}
          disabled={!value.trim()}
          aria-label="Send"
          className="rounded-md p-1.5 text-primary transition-colors hover:bg-accent disabled:opacity-30 disabled:hover:bg-transparent"
        >
          <SendHorizontal className="h-4 w-4" />
        </button>
      </div>
      <p className="mt-1.5 px-1 text-[11px] text-muted-foreground">
        <kbd className="rounded bg-muted px-1">@</kbd> mention an agent ·{" "}
        <kbd className="rounded bg-muted px-1">Enter</kbd> send ·{" "}
        <kbd className="rounded bg-muted px-1">⇧Enter</kbd> newline
      </p>
    </div>
  );
}
