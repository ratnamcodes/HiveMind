"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Maximize, Pause, Play, Volume2, VolumeX } from "lucide-react";
import { cn } from "@/lib/utils";

// The 90-second launch film in a custom player: bright poster with a brand play button, then a
// dark glass control bar with an orange seek bar. Native controls vary too much across browsers.

function fmt(s: number) {
  if (!Number.isFinite(s)) return "0:00";
  const m = Math.floor(s / 60);
  const r = Math.floor(s % 60);
  return `${m}:${r.toString().padStart(2, "0")}`;
}

export function LaunchVideo() {
  const wrapRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const seekRef = useRef<HTMLDivElement>(null);
  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const [started, setStarted] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [time, setTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [buffered, setBuffered] = useState(0);
  const [active, setActive] = useState(true); // controls visible

  const wake = useCallback(() => {
    setActive(true);
    if (idleTimer.current) clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => setActive(false), 2200);
  }, []);

  useEffect(() => () => { if (idleTimer.current) clearTimeout(idleTimer.current); }, []);

  // loadedmetadata can fire before hydration attaches the listener; read what's already there.
  useEffect(() => {
    const v = videoRef.current;
    if (v && Number.isFinite(v.duration) && v.duration > 0) setDuration(v.duration);
  }, []);

  const toggle = useCallback(() => {
    const v = videoRef.current;
    if (!v) return;
    if (v.paused) { setStarted(true); v.play(); } else v.pause();
    wake();
  }, [wake]);

  const seekTo = useCallback((clientX: number) => {
    const v = videoRef.current, bar = seekRef.current;
    if (!v || !bar || !duration) return;
    const r = bar.getBoundingClientRect();
    const frac = Math.min(1, Math.max(0, (clientX - r.left) / r.width));
    v.currentTime = frac * duration;
    setTime(frac * duration);
    wake();
  }, [duration, wake]);

  const fullscreen = useCallback(() => {
    const el = wrapRef.current;
    if (!el) return;
    if (document.fullscreenElement) document.exitFullscreen();
    else el.requestFullscreen?.();
    wake();
  }, [wake]);

  const onKey = useCallback((e: React.KeyboardEvent) => {
    const v = videoRef.current;
    if (!v) return;
    if (e.key === " " || e.key === "k") { e.preventDefault(); toggle(); }
    else if (e.key === "ArrowRight") { v.currentTime = Math.min(v.currentTime + 5, duration); wake(); }
    else if (e.key === "ArrowLeft") { v.currentTime = Math.max(v.currentTime - 5, 0); wake(); }
    else if (e.key === "m") { v.muted = !v.muted; setMuted(v.muted); wake(); }
    else if (e.key === "f") fullscreen();
  }, [toggle, duration, fullscreen, wake]);

  const pct = duration ? (time / duration) * 100 : 0;
  const bufPct = duration ? (buffered / duration) * 100 : 0;
  const showBar = started && (active || !playing);

  return (
    <div
      ref={wrapRef}
      tabIndex={0}
      onKeyDown={onKey}
      onMouseMove={wake}
      onMouseLeave={() => playing && setActive(false)}
      className="group relative overflow-hidden rounded-xl border border-white/10 bg-[#0b0d10] shadow-2xl shadow-black/30 ring-1 ring-black/5 outline-none focus-visible:ring-2 focus-visible:ring-orange-500/60"
    >
      <video
        ref={videoRef}
        playsInline
        preload="metadata"
        poster="/launch-video-poster.png"
        src="/launch-video.mp4"
        className="block aspect-video w-full cursor-pointer"
        onClick={toggle}
        onPlay={() => { setStarted(true); setPlaying(true); wake(); }}
        onPause={() => setPlaying(false)}
        onTimeUpdate={(e) => setTime(e.currentTarget.currentTime)}
        onLoadedMetadata={(e) => setDuration(e.currentTarget.duration)}
        onDurationChange={(e) => setDuration(e.currentTarget.duration)}
        onProgress={(e) => {
          const b = e.currentTarget.buffered;
          if (b.length) setBuffered(b.end(b.length - 1));
        }}
        onEnded={() => { setPlaying(false); setActive(true); }}
      />

      {/* pre-play: bright poster + brand play button */}
      {!started && (
        <button
          type="button"
          onClick={toggle}
          aria-label="Play the launch video"
          className="absolute inset-0 flex cursor-pointer items-center justify-center"
        >
          <span className="flex h-20 w-20 items-center justify-center rounded-full bg-linear-to-b from-orange-400 to-orange-500 shadow-2xl shadow-orange-500/40 ring-1 ring-white/25 transition-transform duration-200 hover:scale-105">
            <Play className="ml-1 h-8 w-8 text-white" fill="currentColor" strokeWidth={0} />
          </span>
          <span className="absolute right-4 bottom-4 rounded-full border border-white/15 bg-black/50 px-2.5 py-1 font-mono text-xs text-zinc-200 backdrop-blur-sm">
            1:30
          </span>
        </button>
      )}

      {/* control bar */}
      <div
        className={cn(
          "absolute inset-x-0 bottom-0 transition-opacity duration-300",
          showBar ? "opacity-100" : "pointer-events-none opacity-0",
        )}
      >
        <div className="bg-linear-to-t from-black/80 via-black/40 to-transparent px-4 pt-10 pb-3">
          {/* seek */}
          <div
            ref={seekRef}
            role="slider"
            aria-label="Seek"
            aria-valuemin={0}
            aria-valuemax={Math.floor(duration)}
            aria-valuenow={Math.floor(time)}
            onPointerDown={(e) => { e.currentTarget.setPointerCapture(e.pointerId); seekTo(e.clientX); }}
            onPointerMove={(e) => e.buttons === 1 && seekTo(e.clientX)}
            className="group/seek relative h-4 cursor-pointer"
          >
            <div className="absolute inset-x-0 top-1/2 h-1 -translate-y-1/2 overflow-hidden rounded-full bg-white/20">
              <div className="absolute inset-y-0 left-0 rounded-full bg-white/25" style={{ width: `${bufPct}%` }} />
              <div className="absolute inset-y-0 left-0 rounded-full bg-linear-to-r from-orange-400 to-orange-500" style={{ width: `${pct}%` }} />
            </div>
            <div
              className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white shadow-md ring-1 ring-black/20 opacity-0 transition-opacity group-hover/seek:opacity-100"
              style={{ left: `${pct}%` }}
            />
          </div>

          <div className="mt-1 flex items-center gap-3">
            <button type="button" onClick={toggle} aria-label={playing ? "Pause" : "Play"} className="text-white/90 transition-colors hover:text-white">
              {playing ? <Pause className="h-5 w-5" fill="currentColor" strokeWidth={0} /> : <Play className="h-5 w-5" fill="currentColor" strokeWidth={0} />}
            </button>
            <button
              type="button"
              onClick={() => { const v = videoRef.current; if (v) { v.muted = !v.muted; setMuted(v.muted); wake(); } }}
              aria-label={muted ? "Unmute" : "Mute"}
              className="text-white/90 transition-colors hover:text-white"
            >
              {muted ? <VolumeX className="h-5 w-5" /> : <Volume2 className="h-5 w-5" />}
            </button>
            <span className="font-mono text-xs text-zinc-300">
              {fmt(time)} <span className="text-zinc-500">/ {fmt(duration)}</span>
            </span>
            <span className="flex-1" />
            <button type="button" onClick={fullscreen} aria-label="Fullscreen" className="text-white/90 transition-colors hover:text-white">
              <Maximize className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
