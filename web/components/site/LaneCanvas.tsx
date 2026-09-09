"use client";

/**
 * The hero's lane, ported from the design canvas.
 *
 * A stream of payments scrolls past as hairlines. Every so often one grows,
 * is marked CONTESTED, then travels back and fades as RETURNED. It is the
 * product in one gesture, and it is the only animation on the site.
 *
 * Under prefers-reduced-motion, and anywhere a 2d context is unavailable, the
 * canvas removes itself and the static fallback behind it shows instead. The
 * loop also stops paying its cost while the tab is hidden.
 */

import { useEffect, useRef } from "react";

export default function LaneCanvas({ onFallback }: { onFallback: (fallback: boolean) => void }) {
  const ref = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const host = canvas.parentElement;
    const context = canvas.getContext && canvas.getContext("2d");
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce || !context || !host) {
      onFallback(true);
      canvas.style.display = "none";
      return;
    }

    let width = 0;
    let height = 0;
    let raf = 0;
    let running = true;

    const resize = () => {
      const rect = host.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = Math.max(1, Math.round(rect.width));
      height = Math.max(1, Math.round(rect.height));
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      context.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();

    let scroll = 0;
    let last = performance.now();
    const ease = (p: number) => 1 - Math.pow(1 - p, 3);
    const rand = (a: number, b: number) => a + Math.random() * (b - a);
    const event: { phase: string; t0: number; nextAt: number; index: number; shift: number } = {
      phase: "idle",
      t0: 0,
      nextAt: last + 2400 + Math.random() * 2000,
      index: 0,
      shift: 0,
    };

    const draw = (t: number) => {
      const spacing = 56 * Math.max(0.78, Math.min(1.4, width / 1440));
      const laneY = Math.round(height * 0.58) + 0.5;
      context.clearRect(0, 0, width, height);
      context.fillStyle = "rgba(27,33,48,1)";
      context.fillRect(0, laneY, width, 1);

      const first = Math.floor(scroll / spacing) - 1;
      const count = Math.ceil(width / spacing) + 3;
      const marked = event.phase === "idle" ? null : event.index;
      context.fillStyle = "rgba(70,84,104,0.78)";
      for (let i = first; i < first + count; i += 1) {
        if (i === marked) continue;
        const x = Math.round(i * spacing - scroll) + 0.5;
        context.fillRect(x, laneY - 72, 1, 72);
      }

      if (event.phase === "idle") {
        if (t >= event.nextAt) {
          event.phase = "grow";
          event.t0 = t;
          event.index = Math.round((scroll + width * rand(0.35, 0.65)) / spacing);
          event.shift = 0;
        }
        return;
      }

      const elapsed = t - event.t0;
      let h = 72;
      let alpha = 1;
      let labelAlpha = 0;
      let label = "CONTESTED";
      let shift = 0;
      if (event.phase === "grow") {
        const p = Math.min(1, elapsed / 400);
        h = 72 + (150 - 72) * ease(p);
        labelAlpha = p;
        if (p >= 1) {
          event.phase = "hold";
          event.t0 = t;
        }
      } else if (event.phase === "hold") {
        h = 150;
        labelAlpha = 1;
        if (elapsed >= 1600) {
          event.phase = "return";
          event.t0 = t;
        }
      } else if (event.phase === "return") {
        const p = Math.min(1, elapsed / 900);
        h = 150;
        label = "RETURNED";
        shift = (width < 720 ? 110 : 220) * ease(p);
        alpha = p > 0.6 ? 1 - (p - 0.6) / 0.4 : 1;
        labelAlpha = alpha;
        if (p >= 1) {
          event.phase = "idle";
          event.nextAt = t + rand(9000, 14000);
          return;
        }
      }

      const x = Math.round(event.index * spacing - scroll + shift) + 0.5;
      context.globalAlpha = alpha;
      context.fillStyle = "#22D3EE";
      context.fillRect(x, laneY - h, 1, h);
      context.fillRect(x, laneY, 1, 58);
      context.globalAlpha = labelAlpha;
      context.font = "500 10px 'Geist Mono', ui-monospace, monospace";
      context.textAlign = "center";
      context.textBaseline = "top";
      if ("letterSpacing" in context) {
        (context as CanvasRenderingContext2D & { letterSpacing: string }).letterSpacing = "2px";
      }
      context.fillText(label, x, laneY + 58 + 10);
      context.globalAlpha = 1;
    };

    const loop = (t: number) => {
      if (!running) return;
      if (document.hidden) {
        last = t;
        raf = requestAnimationFrame(loop);
        return;
      }
      const dt = Math.min(0.1, (t - last) / 1000);
      last = t;
      scroll += 14 * dt;
      draw(t);
      raf = requestAnimationFrame(loop);
    };

    const observer = new ResizeObserver(() => {
      resize();
      draw(performance.now());
    });
    observer.observe(host);
    draw(last);
    raf = requestAnimationFrame(loop);

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      observer.disconnect();
    };
  }, [onFallback]);

  return <canvas id="rc-lane" ref={ref} style={{ display: "block", width: "100%", height: "100%" }} />;
}
