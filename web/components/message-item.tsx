import Link from "next/link";
import { ExternalLink, MessageSquare } from "lucide-react";
import { AGENTS } from "@/lib/agents";
import { formatTime } from "@/lib/format";
import type { Message, MessageLink } from "@/lib/types";
import { cn } from "@/lib/utils";
import { AgentAvatar } from "./agent-avatar";
import { UserAvatar } from "./user-avatar";
import { StatusPill } from "./status-pill";
import { MessageText } from "./message-text";

export function MessageItem({
  message,
  grouped = false,
}: {
  message: Message;
  grouped?: boolean;
}) {
  if (message.author.type === "system") {
    return <SystemMessage message={message} />;
  }

  const isAgent = message.author.type === "agent";
  const meta = isAgent ? AGENTS[message.author.agent] : null;
  const name = isAgent ? meta!.name : message.author.name;

  return (
    <div className={cn("group flex gap-3 px-4 hover:bg-muted/40", grouped ? "py-0.5" : "pt-3 pb-0.5")}>
      <div className="w-9 shrink-0">
        {grouped ? (
          <span className="hidden pt-1 text-right text-[10px] tabular-nums text-muted-foreground group-hover:block">
            {formatTime(message.ts)}
          </span>
        ) : isAgent ? (
          <AgentAvatar agent={message.author.agent} />
        ) : (
          <UserAvatar name={name} />
        )}
      </div>

      <div className="min-w-0 flex-1">
        {!grouped && (
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
            <span className={cn("text-sm font-semibold", meta?.nameColor ?? "text-foreground")}>
              {name}
            </span>
            {isAgent && (
              <span className="rounded bg-muted px-1 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                app
              </span>
            )}
            <span className="text-xs tabular-nums text-muted-foreground">
              {formatTime(message.ts)}
            </span>
            {message.pill && <StatusPill pill={message.pill} />}
          </div>
        )}

        <div className="text-sm leading-relaxed text-foreground/90">
          <MessageText text={message.text} />
        </div>

        {message.links?.length ? (
          <div className="mt-1.5 flex flex-wrap gap-2">
            {message.links.map((l) => (
              <LinkChip key={l.label + l.href} link={l} />
            ))}
          </div>
        ) : null}

        {message.threadId && (
          <Link
            href={`/c/${message.channelId}/t/${message.threadId}`}
            className="mt-1.5 inline-flex items-center gap-1.5 rounded-md border border-transparent px-1.5 py-0.5 text-xs font-medium text-blue-400 hover:border-border hover:bg-card"
          >
            <MessageSquare className="h-3.5 w-3.5" />
            {message.replyCount ?? 0} {message.replyCount === 1 ? "reply" : "replies"}
          </Link>
        )}
      </div>
    </div>
  );
}

function LinkChip({ link }: { link: MessageLink }) {
  const external = link.href.startsWith("http");
  return (
    <a
      href={link.href}
      target={external ? "_blank" : undefined}
      rel={external ? "noreferrer" : undefined}
      className="inline-flex items-center gap-1.5 rounded-md border bg-card px-2 py-1 text-xs text-foreground/80 transition-colors hover:border-ring hover:text-foreground"
    >
      <ExternalLink className="h-3 w-3 text-muted-foreground" />
      {link.label}
    </a>
  );
}

function SystemMessage({ message }: { message: Message }) {
  const isAlert = message.text.startsWith("🚨");
  if (isAlert) {
    return (
      <div className="mx-4 my-2 rounded-lg border border-orange-500/30 bg-orange-500/10 px-4 py-2.5 text-sm leading-relaxed text-orange-200">
        {message.text}
      </div>
    );
  }
  return (
    <div className="flex items-center gap-3 px-4 py-2">
      <span className="h-px flex-1 bg-border" />
      <span className="text-center text-xs text-muted-foreground">{message.text}</span>
      <span className="h-px flex-1 bg-border" />
    </div>
  );
}
