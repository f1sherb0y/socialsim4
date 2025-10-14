import { ReactNode, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";

export function Dropdown({
  anchor,
  open,
  onClose,
  children,
  align = "left",
  matchWidth = true,
  offset = 4,
  maxHeight = 280,
}: {
  anchor: HTMLElement | null;
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  align?: "left" | "right";
  matchWidth?: boolean;
  offset?: number;
  maxHeight?: number;
}) {
  const [rect, setRect] = useState<DOMRect | null>(null);

  useEffect(() => {
    if (!open || !anchor) return;
    const update = () => setRect(anchor.getBoundingClientRect());
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open, anchor]);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => {
      const t = e.target as Node | null;
      if (!t || !(t instanceof HTMLElement)) return;
      // Ignore clicks on the anchor (trigger) itself
      if (anchor && (anchor === t || anchor.contains(t))) return;
      // Close if click is outside the dropdown content
      if (!t.closest(".dropdown-portal")) onClose();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    // Defer binding to avoid immediate close on the opening click
    const id = window.setTimeout(() => {
      document.addEventListener("mousedown", onDoc);
      document.addEventListener("keydown", onKey);
    }, 0);
    return () => {
      window.clearTimeout(id);
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, onClose, anchor]);

  const style = useMemo(() => {
    if (!rect) return undefined as any;
    const width = matchWidth ? rect.width : undefined;
    const baseLeft = align === "left" ? rect.left : rect.right;
    const top = rect.bottom + offset;
    const transform = align === "right" ? "translateX(-100%)" : "none";
    return {
      position: "fixed" as const,
      top,
      left: baseLeft,
      transform,
      width,
      zIndex: 1000,
      maxHeight,
      overflowY: "auto" as const,
    };
  }, [rect, align, matchWidth, offset, maxHeight]);

  if (!open || !anchor || !rect) return null;

  return createPortal(
    <div className="dropdown-portal" style={{ position: "fixed", inset: 0, zIndex: 1000, pointerEvents: "none" }}>
      <div
        className="card select-dropdown"
        style={{ ...style, pointerEvents: "auto", padding: 4, display: "grid", gap: 4 }}
        role="menu"
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}
