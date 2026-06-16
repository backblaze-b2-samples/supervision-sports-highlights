"use client";

import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  ACTIVE_VIDEO_STATUSES,
  type VideoStatus,
} from "@supervision-sports-highlights/shared";

const LABELS: Record<VideoStatus, string> = {
  uploaded: "Queued",
  probing: "Probing",
  detecting: "Detecting",
  clipping: "Cutting clips",
  annotating: "Annotating",
  summarizing: "Summarizing",
  ready: "Ready",
  failed: "Failed",
};

export function isActive(status: VideoStatus): boolean {
  return (ACTIVE_VIDEO_STATUSES as VideoStatus[]).includes(status);
}

export function StatusBadge({ status }: { status: VideoStatus }) {
  const active = isActive(status);
  const variant =
    status === "ready"
      ? "default"
      : status === "failed"
        ? "destructive"
        : "secondary";

  return (
    <Badge variant={variant} className="gap-1.5">
      {active && <Loader2 className="h-3 w-3 animate-spin" />}
      {LABELS[status]}
    </Badge>
  );
}
