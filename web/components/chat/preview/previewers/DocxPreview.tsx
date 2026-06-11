"use client";

import { useEffect, useRef, useState } from "react";
import { AlertCircle, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useBinarySource } from "./useBinarySource";

/**
 * Faithful DOCX preview via ``docx-preview`` (lazy-loaded so the parser only
 * ships when a Word doc is actually opened). It lays the document out as
 * page-shaped HTML with the original styles, which reads far better than the
 * extracted-text fallback. On any parse/layout failure we surface a quiet
 * error — the tab's Download button is the escape hatch.
 */
export default function DocxPreview({ url }: { url: string }) {
  const { t } = useTranslation();
  const src = useBinarySource(url);
  const containerRef = useRef<HTMLDivElement>(null);
  const [rendering, setRendering] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (src.kind === "error") {
      setRendering(false);
      setFailed(true);
      return;
    }
    if (src.kind !== "ready") return;
    const container = containerRef.current;
    if (!container) return;

    let cancelled = false;
    setRendering(true);
    setFailed(false);
    (async () => {
      try {
        const { renderAsync } = await import("docx-preview");
        if (cancelled) return;
        container.innerHTML = "";
        await renderAsync(src.buffer, container, undefined, {
          className: "docx",
          inWrapper: true,
          breakPages: true,
          ignoreLastRenderedPageBreak: true,
          useBase64URL: true,
        });
      } catch {
        if (!cancelled) setFailed(true);
      } finally {
        if (!cancelled) setRendering(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [src]);

  return (
    <div className="relative h-full w-full overflow-y-auto bg-[var(--muted)]/30">
      {rendering && (
        <div className="pointer-events-none absolute inset-0 z-10 flex items-center justify-center">
          <div className="flex items-center gap-2 text-[12px] text-[var(--muted-foreground)]">
            <Loader2 size={14} className="animate-spin" />
            <span>{t("Loading preview…")}</span>
          </div>
        </div>
      )}
      {failed ? (
        <div className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center text-[12px] text-[var(--muted-foreground)]">
          <AlertCircle size={18} strokeWidth={1.7} className="opacity-70" />
          <p>{t("Couldn't render this document — use Download to open it.")}</p>
        </div>
      ) : (
        // docx-preview injects its own page-shaped layout (white pages on a
        // grey deck); the wrapper just gives it room and centres it.
        <div ref={containerRef} className="dt-docx-host py-4" />
      )}
    </div>
  );
}
