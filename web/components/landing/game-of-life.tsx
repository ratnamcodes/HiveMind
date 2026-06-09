"use client";

import { useEffect, useRef } from "react";

// Conway's Game of Life behind the hero: simple local rules giving rise to coordinated, emergent
// behavior — the literal metaphor for a hive mind. Tinted honey-amber, kept subtle on the light
// background.
type Grid = { alive: boolean; opacity: number }[][];

export function GameOfLife() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animationFrameId = 0;
    let timeoutId: ReturnType<typeof setTimeout>;
    const cellSize = 6;
    const cols = Math.floor(canvas.width / cellSize);
    const rows = Math.floor(canvas.height / cellSize);
    const transitionSpeed = 0.18;
    const maxOpacity = 0.4;

    let grid: Grid = Array(rows)
      .fill(null)
      .map(() =>
        Array(cols)
          .fill(null)
          .map(() => ({ alive: Math.random() > 0.85, opacity: Math.random() > 0.85 ? maxOpacity : 0 })),
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
            ctx.fillStyle = `rgba(245, 158, 11, ${cell.opacity})`;
            ctx.beginPath();
            ctx.arc(j * cellSize + cellSize / 2, i * cellSize + cellSize / 2, 1.1, 0, Math.PI * 2);
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
      timeoutId = setTimeout(() => {
        animationFrameId = requestAnimationFrame(draw);
      }, 120);
    };

    draw();
    return () => {
      cancelAnimationFrame(animationFrameId);
      clearTimeout(timeoutId);
    };
  }, []);

  return (
    <div className="pointer-events-none overflow-hidden select-none [mask-image:radial-gradient(rgba(0,0,0,1)_0%,transparent_75%)]">
      <canvas ref={canvasRef} width={1500} height={600} />
    </div>
  );
}
