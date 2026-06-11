"use client";

import { useTranslation } from "react-i18next";
import ComingSoon from "@/components/common/ComingSoon";

/**
 * Mastery Path is hidden from the product nav while it's being reworked. The
 * route is kept so a hand-typed ``/learning`` URL lands on a graceful
 * "coming soon" placeholder instead of a 404. The previous implementation
 * lives in git history; the reusable pieces (``components/learning/*``,
 * ``lib/learning-api.ts``) and the backend (``deeptutor/learning``) are all
 * untouched and ready to be wired back in.
 */
export default function MasteryPathPage() {
  const { t } = useTranslation();
  return <ComingSoon label={t("Mastery Path")} />;
}
