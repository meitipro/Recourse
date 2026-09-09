"use client";

/**
 * The site header, ported from the Claude Design canvas.
 *
 * Every inline style below is the design's own, converted mechanically rather
 * than retyped, so no spacing or colour decision is lost in translation. What
 * this file adds is the state the canvas computed at design time: the viewport
 * width the layout branches on, the mobile menu, and the two group buttons.
 *
 * The canvas had a third view, a component gallery. That is a design system
 * artboard rather than site content, so the group carries the clerk and the
 * feed, which are both real places on this site.
 */

import { useEffect, useState } from "react";

export default function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [vw, setVw] = useState(1280);

  useEffect(() => {
    const onResize = () => {
      const w = window.innerWidth || document.documentElement.clientWidth || 0;
      if (w > 0) setVw(w);
      if (w >= 901) setMenuOpen(false);
    };
    onResize();
    window.addEventListener("resize", onResize);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("resize", onResize);
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

  const wide = vw >= 901;
  const v = {
    goTop: jump("top"),
    goGap: jump("gap"),
    goHow: jump("how"),
    goEval: jump("evaluation"),
    showClerk: jump("clerk"),
    showFeed: jump("feed"),
    linksDisplay: wide ? "flex" : "none",
    burgerDisplay: wide ? "none" : "inline-flex",
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
    bar1Top: menuOpen ? "22px" : "15px",
    bar1Rot: menuOpen ? "45deg" : "0deg",
    bar2Op: menuOpen ? "0" : "1",
    bar2Scale: menuOpen ? "0.6" : "1",
    bar3Top: menuOpen ? "22px" : "29px",
    bar3Rot: menuOpen ? "-45deg" : "0deg",
  };

  return (
    <>
  <header style={{ borderBottom: "1px solid rgba(255,255,255,0.09)", background: "rgba(10,12,18,0.88)", backdropFilter: "blur(10px)", position: "sticky", top: "0", zIndex: "60" } as React.CSSProperties}> <div style={{ padding: "clamp(16px, 1.8vw, 24px) clamp(20px, 5vw, 100px)", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "32px" } as React.CSSProperties}> <a href="#top" onClick={v.goTop} style={{ font: "500 clamp(13px, 1vw, 17px)/1 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.22em", color: "#EEF3F8", flex: "0 0 auto" } as React.CSSProperties}>RECOURSE</a> <nav style={{ display: "flex", alignItems: "center", gap: "clamp(20px, 2.6vw, 48px)", minWidth: "0" } as React.CSSProperties}> <div style={{ display: v.linksDisplay, alignItems: "center", gap: "clamp(20px, 2.6vw, 48px)" } as React.CSSProperties}> <a href="#gap" onClick={v.goGap} style={{ font: "500 clamp(10px, 0.74vw, 13px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.18em", textTransform: "uppercase", color: "#AEB9C8", transition: "color 0.25s ease", whiteSpace: "nowrap" } as React.CSSProperties} className="rc-hover-1">The gap</a> <a href="#how" onClick={v.goHow} style={{ font: "500 clamp(10px, 0.74vw, 13px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.18em", textTransform: "uppercase", color: "#AEB9C8", transition: "color 0.25s ease", whiteSpace: "nowrap" } as React.CSSProperties} className="rc-hover-1">How it works</a> <a href="#evaluation" onClick={v.goEval} style={{ font: "500 clamp(10px, 0.74vw, 13px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.18em", textTransform: "uppercase", color: "#AEB9C8", transition: "color 0.25s ease", whiteSpace: "nowrap" } as React.CSSProperties} className="rc-hover-1">Evaluation</a> </div> <div role="group" style={{ display: v.linksDisplay, alignItems: "stretch", width: "fit-content" } as React.CSSProperties}> <button type="button" onClick={v.showClerk} style={{ display: "inline-flex", alignItems: "center", background: v.navClerkBg, border: "1px solid rgba(255,255,255,0.20)", borderRadius: "0", padding: "clamp(11px, 0.9vw, 15px) clamp(13px, 1.15vw, 22px)", cursor: "pointer", font: "500 clamp(10px, 0.74vw, 13px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", color: v.navClerkColor, transition: "background 0.25s ease, color 0.25s ease", whiteSpace: "nowrap" } as React.CSSProperties} className="rc-hover-2">Clerk</button> <button type="button" onClick={v.showFeed} style={{ display: "inline-flex", alignItems: "center", background: v.navFeedBg, border: "1px solid rgba(255,255,255,0.20)", borderLeft: "0", borderRadius: "0", padding: "clamp(11px, 0.9vw, 15px) clamp(13px, 1.15vw, 22px)", cursor: "pointer", font: "500 clamp(10px, 0.74vw, 13px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", color: v.navFeedColor, transition: "background 0.25s ease, color 0.25s ease", whiteSpace: "nowrap" } as React.CSSProperties} className="rc-hover-2">Feed</button> <button type="button" onClick={v.showFeed} style={{ display: "inline-flex", alignItems: "center", background: v.navFeedBg, border: "1px solid rgba(255,255,255,0.20)", borderLeft: "0", borderRadius: "0", padding: "clamp(11px, 0.9vw, 15px) clamp(13px, 1.15vw, 22px)", cursor: "pointer", font: "500 clamp(10px, 0.74vw, 13px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", color: v.navFeedColor, transition: "background 0.25s ease, color 0.25s ease", whiteSpace: "nowrap" } as React.CSSProperties} className="rc-hover-2">View the feed</button> </div> <button type="button" onClick={v.toggleMenu} aria-label={v.menuAria} aria-expanded={v.menuOpen} aria-controls="mobileMenu" style={{ display: v.burgerDisplay, position: "relative", width: "44px", height: "44px", background: "transparent", border: "0", padding: "0", cursor: "pointer", flex: "0 0 auto" } as React.CSSProperties}> <span style={{ position: "absolute", left: "50%", top: v.bar1Top, width: "22px", height: "1px", background: "#EEF3F8", transform: `translateX(-50%) rotate(${v.bar1Rot})`, transition: "transform 0.45s cubic-bezier(0.16, 1, 0.3, 1), top 0.45s cubic-bezier(0.16, 1, 0.3, 1)" } as React.CSSProperties}> </span> <span style={{ position: "absolute", left: "50%", top: "22px", width: "22px", height: "1px", background: "#EEF3F8", opacity: v.bar2Op, transform: `translateX(-50%) scaleX(${v.bar2Scale})`, transition: "transform 0.45s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease" } as React.CSSProperties}> </span> <span style={{ position: "absolute", left: "50%", top: v.bar3Top, width: "22px", height: "1px", background: "#EEF3F8", transform: `translateX(-50%) rotate(${v.bar3Rot})`, transition: "transform 0.45s cubic-bezier(0.16, 1, 0.3, 1), top 0.45s cubic-bezier(0.16, 1, 0.3, 1)" } as React.CSSProperties}> </span> </button> </nav> </div> </header> <div id="mobileMenu" role="dialog" aria-modal="true" aria-label="Site menu" aria-hidden={v.menuHidden} onClick={v.closeMenu} style={{ position: "fixed", inset: "0", zIndex: "50", background: "rgba(10,12,18,0.95)", backdropFilter: "blur(28px) saturate(130%)", clipPath: v.menuClip, opacity: v.menuOpacity, pointerEvents: v.menuEvents, transition: "clip-path 0.7s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.45s ease", display: "flex", alignItems: "center", justifyContent: "center" } as React.CSSProperties}> <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "28px", padding: "24px" } as React.CSSProperties}> <a href="#gap" onClick={v.goGap} style={{ font: "500 clamp(20px, 5.5vw, 28px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8", opacity: v.menuItemOp, transform: `translateY(${v.menuItemY})`, transition: "opacity 0.4s ease 180ms, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1) 180ms" } as React.CSSProperties}>The gap</a> <a href="#how" onClick={v.goHow} style={{ font: "500 clamp(20px, 5.5vw, 28px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8", opacity: v.menuItemOp, transform: `translateY(${v.menuItemY})`, transition: "opacity 0.4s ease 250ms, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1) 250ms" } as React.CSSProperties}>How it works</a> <a href="#evaluation" onClick={v.goEval} style={{ font: "500 clamp(20px, 5.5vw, 28px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.14em", textTransform: "uppercase", color: "#EEF3F8", opacity: v.menuItemOp, transform: `translateY(${v.menuItemY})`, transition: "opacity 0.4s ease 320ms, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1) 320ms" } as React.CSSProperties}>Evaluation</a> <button type="button" onClick={v.showClerk} style={{ background: "transparent", border: "0", padding: "0", cursor: "pointer", font: "500 clamp(20px, 5.5vw, 28px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", color: "#EEF3F8", opacity: v.menuItemOp, transform: `translateY(${v.menuItemY})`, transition: "opacity 0.4s ease 390ms, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1) 390ms" } as React.CSSProperties}>Clerk</button> <button type="button" onClick={v.showFeed} style={{ marginTop: "12px", background: "transparent", border: "1px solid rgba(255,255,255,0.20)", borderRadius: "0", padding: "16px 40px", cursor: "pointer", font: "500 clamp(12px, 3vw, 14px) 'Geist Mono', ui-monospace, monospace", letterSpacing: "0.04em", color: "#EEF3F8", opacity: v.menuItemOp, transform: `translateY(${v.menuItemY})`, transition: "opacity 0.4s ease 460ms, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1) 460ms" } as React.CSSProperties}>View the feed</button> </div> </div>
    </>
  );
}
