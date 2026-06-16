"use client";

import Link from "next/link";
import Image from "next/image";
import { Clapperboard, Film, Clock } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "./status-badge";
import { useVideos } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

function fmtDuration(seconds: number | null): string {
  if (!seconds) return "—";
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function HighlightsLibrary() {
  const { data: videos = [], isLoading, error, refetch } = useVideos();

  if (isLoading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-56 w-full rounded-md" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  if (videos.length === 0) {
    return (
      <Card>
        <CardContent className="p-0">
          <EmptyState
            icon={Clapperboard}
            title="No analyzed videos yet"
            description="Upload a sports clip to generate highlights."
            action={
              <Button asChild size="sm">
                <Link href="/upload">Upload a clip</Link>
              </Button>
            }
          />
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {videos.map((v) => (
        <Link key={v.id} href={`/highlights/${v.id}`} className="group">
          <Card className="card-hover overflow-hidden h-full">
            <div className="relative aspect-video bg-muted overflow-hidden">
              {v.thumb_url ? (
                <Image
                  src={v.thumb_url}
                  alt={v.filename}
                  fill
                  unoptimized
                  className="object-cover transition-transform group-hover:scale-105"
                />
              ) : (
                <div className="flex h-full items-center justify-center">
                  <Film className="h-8 w-8 text-muted-foreground" />
                </div>
              )}
              <div className="absolute top-2 right-2">
                <StatusBadge status={v.status} />
              </div>
            </div>
            <CardContent className="p-4 space-y-2">
              <p className="text-sm font-semibold truncate">{v.filename}</p>
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                  <Clapperboard className="h-3.5 w-3.5" />
                  {v.moment_count} moment{v.moment_count === 1 ? "" : "s"}
                </span>
                <span className="inline-flex items-center gap-1 tabular-nums">
                  <Clock className="h-3.5 w-3.5" />
                  {fmtDuration(v.duration_seconds)}
                </span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                {formatDate(v.created_at)}
              </p>
            </CardContent>
          </Card>
        </Link>
      ))}
    </div>
  );
}
