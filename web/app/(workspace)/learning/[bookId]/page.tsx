"use client";

import { useTranslation } from "react-i18next";
import ComingSoon from "@/components/common/ComingSoon";

/**
 * Per-book Mastery Path runner — shelved alongside the index route (see
 * ``../page.tsx``). Kept as a "coming soon" placeholder so deep links don't
 * 404; the original runner is in git history and the backend/components are
 * intact.
 */
export default function MasteryPathBookPage() {
  const { t } = useTranslation();
  return <ComingSoon label={t("Mastery Path")} />;
}
