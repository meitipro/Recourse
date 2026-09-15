"use client";

/**
 * The boot screen, ported from the canvas's RecourseBoot.
 *
 * The canvas drove its labels off a clock: "Reading eval/cases.json - case 07
 * of 18" stepped past every 44 milliseconds while nothing was being read.
 * Every label here names something this page did or is waiting on. The server
 * read the committed cases and the freeze record to render the page, so those
 * two labels say "Read from", and the counter steps through the case ids that
 * were read. The fonts label waits on document.fonts.ready and the lane label
 * on the lane's first frame. The clock paces the steps and stands for no work.
 *
 * Nothing may trap the page. A failsafe finishes it at 3.6 seconds whatever it
 * reached, a CSS animation in globals.css takes it away at four seconds even
 * where no script runs, and under reduced motion it never shows.
 */

import { useEffect, useRef, useState } from "react";

import { list, spell } from "@/lib/words";

import { laneStarted } from "./LaneCanvas";

const WORDS = ["Honored", "Not honored", "Unclear"];

export default function Boot({ cases, networks }: { cases: string[]; networks: string[] }) {
  const [pct, setPct] = useState(0);
  const [label, setLabel] = useState("Read from eval/cases.json");
  const [word, setWord] = useState(0);
  const [done, setDone] = useState(false);
  const [gone, setGone] = useState(false);
  const finished = useRef(false);

  useEffect(() => {
    let alive = true;
    const timers: ReturnType<typeof setTimeout>[] = [];
    const wait = (ms: number) => new Promise<void>((resolve) => void timers.push(setTimeout(resolve, ms)));
    const live = () => alive && !finished.current;
    const set = (to: number, text: string) => {
      if (live()) {
        setPct(to);
        setLabel(text);
      }
    };
    const words = setInterval(() => {
      if (live()) setWord((at) => (at + 1) % WORDS.length);
    }, 900);
    const finish = () => {
      if (!alive || finished.current) return;
      finished.current = true;
      clearInterval(words);
      setPct(100);
      setLabel("Ready");
      setDone(true);
      timers.push(setTimeout(() => alive && setGone(true), 540));
    };

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      finished.current = true;
      clearInterval(words);
      setDone(true);
      setGone(true);
    } else {
      timers.push(setTimeout(finish, 3600));
      void (async () => {
        for (let i = 0; i < cases.length; i += 1) {
          await wait(44);
          set(Math.round(((i + 1) / cases.length) * 55), `Read from eval/cases.json - case ${cases[i]} of ${cases.length}`);
        }
        set(62, "Loading Source Serif 4, Work Sans, Geist Mono");
        try {
          await document.fonts?.ready;
        } catch {
          // A browser without the font loading API has nothing to wait on.
        }
        if (networks.length) {
          const count = `${spell(networks.length)} deployment${networks.length === 1 ? "" : "s"}`;
          set(80, `Read from contracts/FROZEN.json - ${count}, ${list(networks)}`);
          await wait(170);
        }
        set(92, "Starting the settlement lane");
        await laneStarted;
        await wait(230);
        finish();
      })();
    }

    return () => {
      alive = false;
      clearInterval(words);
      timers.forEach((timer) => clearTimeout(timer));
    };
  }, [cases, networks]);

  const v = {
    count: String(pct).padStart(3, "0"),
    scale: String(pct / 100),
    word: WORDS[word],
    wordOp: done ? "0" : "1",
    wordY: done ? "-10px" : "0px",
    display: gone ? "none" : "block",
    opacity: done ? "0" : "1",
    events: done ? "none" : "auto",
  };

  return (
    <div id="rc-boot" className="rc-boot" role="status" aria-live="polite" aria-hidden={gone} style={{ position: "fixed", inset: "0", zIndex: "9999", background: "#0A0C12", display: v.display, opacity: v.opacity, pointerEvents: v.events, transition: "opacity 0.5s ease" } as React.CSSProperties}>
      <div style={{ position: "absolute", top: "clamp(20px, 3vw, 34px)", left: "clamp(20px, 5vw, 100px)", font: "500 11px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.3em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>Recourse</div>
      <div style={{ position: "absolute", top: "50%", left: "clamp(20px, 5vw, 100px)", right: "clamp(20px, 5vw, 100px)", transform: "translateY(-50%)" } as React.CSSProperties}>
        <div style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontStyle: "italic", fontWeight: "600", fontSize: "clamp(34px, 7vw, 74px)", lineHeight: "1", letterSpacing: "-0.03em", color: "#EEF3F8", opacity: v.wordOp, transform: `translateY(${v.wordY})`, transition: "opacity 0.3s ease, transform 0.3s ease" } as React.CSSProperties}>{v.word}</div>
        <div style={{ marginTop: "20px", font: "400 11px/1.7 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.1em", textTransform: "uppercase", color: "#7C8798" } as React.CSSProperties}>{label}</div>
      </div>
      <div style={{ position: "absolute", bottom: "clamp(48px, 6vw, 78px)", right: "clamp(20px, 5vw, 100px)", font: "500 clamp(56px, 11vw, 132px)/1 'Geist Mono', ui-monospace, monospace", letterSpacing: "-0.04em", color: "#EEF3F8", fontVariantNumeric: "tabular-nums" } as React.CSSProperties}>{v.count}</div>
      <div style={{ position: "absolute", bottom: "0", left: "0", right: "0", height: "3px", background: "#1B2130" } as React.CSSProperties}>
        <div style={{ height: "3px", background: "#22D3EE", transform: `scaleX(${v.scale})`, transformOrigin: "left center", transition: "transform 0.2s linear" } as React.CSSProperties}></div>
      </div>
    </div>
  );
}
