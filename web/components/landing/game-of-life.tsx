"use client";

import { useEffect, useRef } from "react";

// Conway's Game of Life behind the hero: simple local rules giving rise to coordinated, emergent
// behavior — the literal metaphor for a hive mind. Tinted honey-amber and kept clearly visible
// (like the Solar template's generative grid), masked to fade toward the edges.
type Grid = { alive: boolean; opacity: number }[][];

export function GameOfLife() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduce =
      typeof window !== "undefined" &&
      typeof window.matchMedia === "function" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let animationFrameId = 0;
    let timeoutId: ReturnType<typeof setTimeout>;
    const cellSize = 8;
    const cols = Math.floor(canvas.width / cellSize);
    const rows = Math.floor(canvas.height / cellSize);
    const transitionSpeed = 0.16;
    const maxOpacity = 0.38;

    let grid: Grid = Array(rows)
      .fill(null)
      .map(() =>
        Array(cols)
          .fill(null)
          .map(() => {
            const alive = Math.random() > 0.72;
            return { alive, opacity: alive ? maxOpacity : 0 };
          }),
      );

    const countNeighbors = (g: Grid, x: number, y: number): number => {
      let sum = 0;
      for (let i = -1; i < 2; i++) {
        for (let j = -1; j < 2; j++) {
          const row = (x + i + rows) % rows;
          const col = (y + j + cols) % cols;
          sum += g[row][col].alive ? 1 : 0;
        }
      }
      sum -= g[x][y].alive ? 1 : 0;
      return sum;
    };

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < rows; i++) {
        for (let j = 0; j < cols; j++) {
          const cell = grid[i][j];
          if (cell.alive && cell.opacity < maxOpacity) {
            cell.opacity = Math.min(cell.opacity + transitionSpeed, maxOpacity);
          } else if (!cell.alive && cell.opacity > 0) {
            cell.opacity = Math.max(cell.opacity - transitionSpeed, 0);
          }
          if (cell.opacity > 0) {
            // warm near-black dots (stone-800) — high contrast on gray-50, like the template's grid
            ctx.fillStyle = `rgba(41, 37, 36, ${cell.opacity})`;
            ctx.beginPath();
            ctx.arc(j * cellSize + cellSize / 2, i * cellSize + cellSize / 2, 1.5, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
      grid = grid.map((row, i) =>
        row.map((cell, j) => {
          const neighbors = countNeighbors(grid, i, j);
          const willBeAlive = cell.alive ? neighbors >= 2 && neighbors <= 3 : neighbors === 3;
          return { alive: willBeAlive, opacity: cell.opacity };
        }),
      );
      if (reduce) return; // honor reduced-motion: draw a single static frame
      timeoutId = setTimeout(() => {
        animationFrameId = requestAnimationFrame(draw);
      }, 130);
    };

    draw();
    return () => {
      cancelAnimationFrame(animationFrameId);
      clearTimeout(timeoutId);
    };
  }, []);

  return (
    <div className="pointer-events-none overflow-hidden select-none [mask-image:radial-gradient(circle_at_center,#000_0%,#000_18%,transparent_82%)]">
      <canvas ref={canvasRef} width={1700} height={760} />
    </div>
  );
}
