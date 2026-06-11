"use client";

/**
 * Compact composer for partner chat — a chat-style rounded card: full-width
 * auto-sizing textarea with an inline send button. (SimpleComposerInput is a
 * bare `flex-1` textarea that collapses outside a flex row; this owns its
 * own shell instead.)
 */

import { memo, useCallback, useRef, useState } from "react";
import { ArrowUp } from "lucide-react";
import { useTranslation } from "react-i18next";
import { shouldSubmitOnEnter } from "@/lib/composer-keyboard";
import { useAutoSizedTextarea } from "@/lib/use-auto-sized-textarea";

export const PartnerComposer = memo(function PartnerComposer({
  onSend,
  disabled,
  placeholder,
}: {
  onSend: (content: string) => void;
  disabled?: boolean;
  placeholder?: string;
}) {
  const { t } = useTranslation();
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const isComposingRef = useRef(false);

  useAutoSizedTextarea(textareaRef, input, { min: 24, max: 180 });

  const submit = useCallback(() => {
    const content = input.trim();
    if (!content || disabled) return;
    onSend(content);
    setInput("");
    requestAnimationFrame(() => textareaRef.current?.focus());
  }, [input, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (shouldSubmitOnEnter(e, isComposingRef.current)) {
        e.preventDefault();
        submit();
      }
    },
    [submit],
  );

  return (
    <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] shadow-sm transition-colors focus-within:border-[var(--ring)]">
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        onCompositionStart={() => {
          isComposingRef.current = true;
        }}
        onCompositionEnd={() => {
          // Some IMEs fire compositionend before the confirming Enter
          // keydown — keep the guard through the current event turn.
          setTimeout(() => {
            isComposingRef.current = false;
          }, 0);
        }}
        placeholder={placeholder ?? t("Type a message...")}
        rows={1}
        maxLength={32000}
        disabled={disabled}
        className="block w-full resize-none bg-transparent px-3.5 pt-3 pb-1 text-[14px] leading-relaxed text-[var(--foreground)] outline-none placeholder:text-[var(--muted-foreground)] disabled:opacity-50"
      />
      <div className="flex items-center justify-end px-2 pb-2">
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !input.trim()}
          aria-label={t("Send")}
          className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--primary)] text-[var(--primary-foreground)] transition-opacity hover:opacity-90 disabled:opacity-30"
        >
          <ArrowUp className="h-4 w-4" strokeWidth={2.2} />
        </button>
      </div>
    </div>
  );
});
