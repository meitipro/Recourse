"use client";

/**
 * The site header, ported from the Claude Design canvas.
 *
 * The second export made it a floating bar: fixed, centred, an R mark, the
 * wordmark, the section links and the group, with an edge that firms up once
 * the page has scrolled a hundred pixels. Every inline style is the design's
 * own. What this file adds is the state the canvas computed at design time:
 * the scroll edge, the mobile menu, and the group's buttons.
 *
 * The canvas chose between the wide bar and the menu button by a viewport
 * width it held in state. Here that choice is two classes and a media query in
 * globals.css, so the server's HTML is already right on a phone rather than
 * drawing the wide bar there until the script runs.
 *
 * The canvas had a third view, a component gallery. That is a design system
 * artboard rather than site content, so the group carries the clerk and the
 * feed, which are both real places on this site.
 */

import { useEffect, useState } from "react";

const LINK = { display: "inline-flex", alignItems: "center", padding: "10px 13px", font: "500 clamp(10px, 0.72vw, 12.5px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", color: "#AEB9C8", transition: "color 0.25s ease, background 0.25s ease", whiteSpace: "nowrap" } as React.CSSProperties;

const RULE = { width: "1px", height: "20px", background: "#263048", margin: "0 6px", flex: "0 0 auto" } as React.CSSProperties;

const GROUP = { display: "inline-flex", alignItems: "center", border: "1px solid rgba(255,255,255,0.20)", borderRadius: "0", padding: "10px clamp(11px, 0.95vw, 16px)", cursor: "pointer", font: "500 clamp(10px, 0.72vw, 12.5px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", transition: "background 0.25s ease, color 0.25s ease", whiteSpace: "nowrap" } as React.CSSProperties;

export default function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onResize = () => {
      const w = window.innerWidth || document.documentElement.clientWidth || 0;
      if (w >= 901) setMenuOpen(false);
    };
    const onScroll = () => setScrolled((window.scrollY || 0) > 100);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    onScroll();
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  useEffect(() => {
    document.body.style.overflow = menuOpen ? "hidden" : "";
    return () => {
      document.body.style.overflow = "";
    };
  }, [menuOpen]);

  const jump = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    setMenuOpen(false);
    const go = () => {
      if (id === "top") {
        window.scrollTo({ top: 0, behavior: "smooth" });
        return;
      }
      const el = document.getElementById(id);
      if (el) {
        window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 72, behavior: "smooth" });
      }
    };
    setTimeout(go, menuOpen ? 60 : 0);
  };

  const v = {
    goTop: jump("top"),
    goGap: jump("gap"),
    goHow: jump("how"),
    goEval: jump("evaluation"),
    showClerk: jump("clerk"),
    showFeed: jump("feed"),
    barEdge: scrolled ? "rgba(255,255,255,0.20)" : "rgba(255,255,255,0.10)",
    navClerkBg: "transparent",
    navClerkColor: "#AEB9C8",
    navFeedBg: "transparent",
    navFeedColor: "#AEB9C8",
    toggleMenu: () => setMenuOpen((open) => !open),
    closeMenu: () => setMenuOpen(false),
    menuAria: menuOpen ? "Close menu" : "Open menu",
    menuOpen: menuOpen,
    menuHidden: !menuOpen,
    menuOpacity: menuOpen ? "1" : "0",
    menuEvents: menuOpen ? "auto" : "none",
    menuClip: menuOpen ? "inset(0 0 0 0)" : "inset(0 0 100% 0)",
    menuItemY: menuOpen ? "0px" : "8px",
    menuItemOp: menuOpen ? "1" : "0",
    bar1Top: menuOpen ? "19px" : "12px",
    bar1Rot: menuOpen ? "45deg" : "0deg",
    bar2Op: menuOpen ? "0" : "1",
    bar2Scale: menuOpen ? "0.6" : "1",
    bar3Top: menuOpen ? "19px" : "26px",
    bar3Rot: menuOpen ? "-45deg" : "0deg",
  };

  return (
    <>
      <header style={{ position: "fixed", top: "0", left: "0", right: "0", zIndex: "60", display: "flex", justifyContent: "center", padding: "clamp(12px, 1.6vw, 20px) clamp(14px, 4vw, 28px)", pointerEvents: "none" } as React.CSSProperties}>
        <nav aria-label="Site" style={{ pointerEvents: "auto", display: "inline-flex", alignItems: "center", maxWidth: "100%", border: `1px solid ${v.barEdge}`, background: "rgba(14,17,25,0.86)", backdropFilter: "blur(14px) saturate(130%)", padding: "7px", transition: "border-color 0.3s ease" } as React.CSSProperties}>
          <a href="#top" onClick={v.goTop} aria-label="Recourse, back to top" style={{ flex: "0 0 auto", width: "38px", height: "38px", borderRadius: "50%", border: "1px solid rgba(34,211,238,0.5)", display: "inline-flex", alignItems: "center", justifyContent: "center", transition: "transform 0.25s ease, border-color 0.25s ease" } as React.CSSProperties} className="rc-hover-8">
            <span style={{ fontFamily: "'Source Serif 4', Georgia, serif", fontStyle: "italic", fontWeight: "600", fontSize: "15px", color: "#EEF3F8" } as React.CSSProperties}>R</span>
          </a>
          <a href="#top" onClick={v.goTop} className="rc-wide" style={{ alignItems: "center", padding: "0 4px 0 12px", font: "500 12px 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.22em", color: "#EEF3F8", whiteSpace: "nowrap" } as React.CSSProperties}>RECOURSE</a>
          <span aria-hidden="true" className="rc-wide" style={RULE}></span>
          <div className="rc-wide" style={{ alignItems: "center" } as React.CSSProperties}>
            <a href="#gap" onClick={v.goGap} style={LINK} className="rc-hover-2">The gap</a>
            <a href="#how" onClick={v.goHow} style={LINK} className="rc-hover-2">How it works</a>
            <a href="#evaluation" onClick={v.goEval} style={LINK} className="rc-hover-2">Evaluation</a>
          </div>
          <span aria-hidden="true" className="rc-wide" style={RULE}></span>
          <div role="group" className="rc-wide" style={{ alignItems: "stretch" } as React.CSSProperties}>
            <button type="button" onClick={v.showClerk} style={{ ...GROUP, background: v.navClerkBg, color: v.navClerkColor }} className="rc-hover-2">Clerk</button>
            <button type="button" onClick={v.showFeed} style={{ ...GROUP, borderLeft: "0", background: v.navFeedBg, color: v.navFeedColor }} className="rc-hover-2">Feed</button>
            <button type="button" onClick={v.showFeed} style={{ ...GROUP, borderLeft: "0", background: v.navFeedBg, color: v.navFeedColor }} className="rc-hover-2">View the feed</button>
          </div>
          <button type="button" onClick={v.toggleMenu} aria-label={v.menuAria} aria-expanded={v.menuOpen} aria-controls="mobileMenu" className="rc-narrow" style={{ position: "relative", width: "44px", height: "38px", background: "transparent", border: "0", padding: "0", cursor: "pointer", flex: "0 0 auto" } as React.CSSProperties}>
            <span style={{ position: "absolute", left: "50%", top: v.bar1Top, width: "22px", height: "1px", background: "#EEF3F8", transform: `translateX(-50%) rotate(${v.bar1Rot})`, transition: "transform 0.45s cubic-bezier(0.16, 1, 0.3, 1), top 0.45s cubic-bezier(0.16, 1, 0.3, 1)" } as React.CSSProperties}></span>
            <span style={{ position: "absolute", left: "50%", top: "19px", width: "22px", height: "1px", background: "#EEF3F8", opacity: v.bar2Op, transform: `translateX(-50%) scaleX(${v.bar2Scale})`, transition: "transform 0.45s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease" } as React.CSSProperties}></span>
            <span style={{ position: "absolute", left: "50%", top: v.bar3Top, width: "22px", height: "1px", background: "#EEF3F8", transform: `translateX(-50%) rotate(${v.bar3Rot})`, transition: "transform 0.45s cubic-bezier(0.16, 1, 0.3, 1), top 0.45s cubic-bezier(0.16, 1, 0.3, 1)" } as React.CSSProperties}></span>
          </button>
        </nav>
      </header>
      <div id="mobileMenu" role="dialog" aria-modal="true" aria-label="Site menu" aria-hidden={v.menuHidden} onClick={v.closeMenu} style={{ position: "fixed", inset: "0", zIndex: "50", background: "rgba(10,12,18,0.95)", backdropFilter: "blur(28px) saturate(130%)", clipPath: v.menuClip, opacity: v.menuOpacity, pointerEvents: v.menuEvents, transition: "clip-path 0.7s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.45s ease", display: "flex", alignItems: "center", justifyContent: "center" } as React.CSSProperties}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "28px", padding: "24px" } as React.CSSProperties}>
          <a href="#gap" onClick={v.goGap} style={{ font: "500 clamp(20px, 5.5vw, 28px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8", opacity: v.menuItemOp, transform: `translateY(${v.menuItemY})`, transition: "opacity 0.4s ease 180ms, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1) 180ms" } as React.CSSProperties}>The gap</a>
          <a href="#how" onClick={v.goHow} style={{ font: "500 clamp(20px, 5.5vw, 28px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8", opacity: v.menuItemOp, transform: `translateY(${v.menuItemY})`, transition: "opacity 0.4s ease 250ms, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1) 250ms" } as React.CSSProperties}>How it works</a>
          <a href="#evaluation" onClick={v.goEval} style={{ font: "500 clamp(20px, 5.5vw, 28px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8", opacity: v.menuItemOp, transform: `translateY(${v.menuItemY})`, transition: "opacity 0.4s ease 320ms, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1) 320ms" } as React.CSSProperties}>Evaluation</a>
          <button type="button" onClick={v.showClerk} style={{ background: "transparent", border: "0", padding: "0", cursor: "pointer", font: "500 clamp(20px, 5.5vw, 28px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", color: "#EEF3F8", opacity: v.menuItemOp, transform: `translateY(${v.menuItemY})`, transition: "opacity 0.4s ease 390ms, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1) 390ms" } as React.CSSProperties}>Clerk</button>
          <button type="button" onClick={v.showFeed} style={{ marginTop: "12px", background: "transparent", border: "1px solid rgba(255,255,255,0.20)", borderRadius: "0", padding: "16px 40px", cursor: "pointer", font: "500 clamp(12px, 3vw, 14px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", color: "#EEF3F8", opacity: v.menuItemOp, transform: `translateY(${v.menuItemY})`, transition: "opacity 0.4s ease 460ms, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1) 460ms" } as React.CSSProperties}>View the feed</button>
        </div>
      </div>
    </>
  );
}
