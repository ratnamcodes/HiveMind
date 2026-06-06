"use client";

import { useEffect, type ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { CheckCircle2, Hash } from "lucide-react";
import { useWarRoom } from "@/lib/store";
import { SEVERITY } from "@/lib/severity";
import type { Channel } from "@/lib/types";
import { cn } from "@/lib/utils";

export function ChannelSidebar() {
  const channels = useWarRoom((s) => s.channels);
  const loadChannels = useWarRoom((s) => s.loadChannels);
  const pathname = usePathname();

  useEffect(() => {
    loadChannels();
  }, [loadChannels]);

  const ops = channels.filter((c) => c.kind === "ops");
  const incidents = channels.filter((c) => c.kind === "incident");

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      <header className="flex h-14 items-center gap-2.5 border-b border-sidebar-border px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-400 to-orange-500 text-base shadow-sm">
          🐝
        </div>
        <div className="leading-tight">
          <div className="text-sm font-bold tracking-tight">HiveMind</div>
          <div className="text-[11px] text-muted-foreground">War Room</div>
        </div>
      </header>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        <SectionLabel>Pinned</SectionLabel>
        {ops.map((c) => (
          <ChannelRow key={c.id} channel={c} active={pathname === `/c/${c.id}`} />
        ))}

        <SectionLabel className="pt-4">Incidents</SectionLabel>
        {incidents.map((c) => (
          <ChannelRow
            key={c.id}
            channel={c}
            active={pathname.startsWith(`/c/${c.id}`)}
          />
        ))}
        {incidents.length === 0 && (
          <p className="px-3 py-1 text-xs text-muted-foreground">
            No active incidents
          </p>
        )}
      </nav>

      <footer className="border-t border-sidebar-border px-4 py-2.5 text-[11px] text-muted-foreground">
        6 agents · mock backend
      </footer>
    </aside>
  );
}

function SectionLabel({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "px-3 pb-1 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground",
        className,
      )}
    >
      {children}
    </div>
  );
}

function ChannelRow({ channel, active }: { channel: Channel; active: boolean }) {
  const sev = channel.severity ? SEVERITY[channel.severity] : null;
  const hasUnread = channel.unread > 0;

  return (
    <Link
      href={`/c/${channel.id}`}
      className={cn(
        "relative flex items-center gap-2 rounded-md py-1.5 pl-3 pr-2 text-sm transition-colors",
        active
          ? "bg-sidebar-accent text-sidebar-accent-foreground"
          : "text-sidebar-foreground/75 hover:bg-sidebar-accent/50",
      )}
    >
      {sev && (
        <span
          className={cn(
            "absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r",
            sev.stripe,
            channel.resolved && "opacity-40",
          )}
        />
      )}
      {channel.resolved ? (
        <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      ) : (
        <Hash className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
      )}
      <span
        className={cn(
          "truncate",
          hasUnread && !active && "font-semibold text-sidebar-foreground",
          channel.resolved && "text-muted-foreground",
        )}
      >
        {channel.name}
      </span>

      {channel.isNew ? (
        <span className="relative ml-auto flex h-2 w-2 shrink-0">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-orange-400 opacity-75" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-orange-500" />
        </span>
      ) : hasUnread ? (
        <span className="ml-auto shrink-0 rounded-full bg-primary px-1.5 text-[10px] font-semibold text-primary-foreground">
          {channel.unread}
        </span>
      ) : null}
    </Link>
  );
}
