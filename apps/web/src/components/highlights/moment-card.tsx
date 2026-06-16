"use client";

import { Users, Tag, Activity, Circle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { MomentPlayback } from "@supervision-sports-highlights/shared";

function fmtRange(start: number, end: number): string {
  const f = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };
  return `${f(start)} – ${f(end)}`;
}

export function MomentCard({ item }: { item: MomentPlayback }) {
  const { moment, clip_url } = item;

  return (
    <Card className="overflow-hidden">
      <div className="grid md:grid-cols-[280px_1fr]">
        <div className="bg-black aspect-video md:aspect-auto">
          {clip_url ? (
            // Highlight clip streamed straight from a presigned B2 GET URL.
            <video
              src={clip_url}
              controls
              playsInline
              preload="metadata"
              poster={item.thumb_url ?? undefined}
              className="h-full w-full object-contain"
            />
          ) : (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
              Clip unavailable
            </div>
          )}
        </div>

        <CardContent className="p-4 space-y-3">
          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-xs text-muted-foreground tabular-nums">
              {fmtRange(moment.start_s, moment.end_s)}
            </span>
            <Badge variant="outline" className="gap-1">
              <Activity className="h-3 w-3" />
              {(moment.score * 100).toFixed(0)}%
            </Badge>
          </div>

          {moment.summary && (
            <p className="text-sm font-semibold">{moment.summary}</p>
          )}
          {moment.description && (
            <p className="text-sm text-muted-foreground">{moment.description}</p>
          )}

          <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1">
              <Users className="h-3.5 w-3.5" />
              {moment.peak_person_count} peak · {moment.unique_track_ids} tracked
            </span>
            <span className="inline-flex items-center gap-1">
              <Circle className="h-3.5 w-3.5" />
              {moment.ball_present ? "ball in play" : "no ball"}
            </span>
          </div>

          {moment.tags.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              <Tag className="h-3.5 w-3.5 text-muted-foreground" />
              {moment.tags.map((t) => (
                <Badge key={t} variant="secondary" className="text-[10px]">
                  {t}
                </Badge>
              ))}
            </div>
          )}
        </CardContent>
      </div>
    </Card>
  );
}
