"use client";

import { Film } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useVideoPlayback } from "@/lib/queries";

/**
 * Supervision-annotated full video. The <video> element streams (and seeks
 * via HTTP range requests) directly from a presigned B2 GET URL — the API
 * never proxies the bytes.
 */
export function AnnotatedPlayer({
  videoId,
  ready,
}: {
  videoId: string;
  ready: boolean;
}) {
  const { data, isLoading } = useVideoPlayback(videoId, ready);

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Annotated video</CardTitle>
      </CardHeader>
      <CardContent className="p-0">
        <div className="aspect-video bg-black">
          {ready && data?.url ? (
            <video
              key={data.url}
              src={data.url}
              controls
              playsInline
              className="h-full w-full"
            />
          ) : isLoading || !ready ? (
            <Skeleton className="h-full w-full rounded-none" />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              <Film className="h-8 w-8" />
              <p className="text-sm">Annotated video not available yet</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
