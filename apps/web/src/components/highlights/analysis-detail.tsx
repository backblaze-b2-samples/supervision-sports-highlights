"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft,
  Info,
  RefreshCw,
  Search,
  Sparkles,
  Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge, isActive } from "./status-badge";
import { AnnotatedPlayer } from "./annotated-player";
import { MomentCard } from "./moment-card";
import {
  useDeleteVideo,
  useReanalyzeVideo,
  useVideo,
  useVideoMoments,
} from "@/lib/queries";

export function AnalysisDetail({ videoId }: { videoId: string }) {
  const router = useRouter();
  const { data: video, isLoading, error, refetch } = useVideo(videoId);
  const ready = video?.status === "ready";
  const { data: moments = [] } = useVideoMoments(videoId, !!ready);
  const del = useDeleteVideo();
  const reanalyze = useReanalyzeVideo();
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return moments;
    return moments.filter((m) => {
      const hay = `${m.moment.summary} ${m.moment.description} ${m.moment.tags.join(
        " "
      )}`.toLowerCase();
      return hay.includes(q);
    });
  }, [moments, query]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="aspect-video w-full rounded-md" />
      </div>
    );
  }

  if (error || !video) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const handleDelete = () => {
    del.mutate(videoId, {
      onSuccess: () => {
        toast.success("Video and its highlights deleted");
        router.push("/highlights");
      },
      onError: (e) => toast.error(`Delete failed: ${e.message}`),
    });
  };

  const handleReanalyze = () => {
    reanalyze.mutate(videoId, {
      onSuccess: () => toast.success("Re-analysis started"),
      onError: (e) => toast.error(`Re-analyze failed: ${e.message}`),
    });
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
        <div className="flex items-center gap-3 min-w-0">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 shrink-0"
            onClick={() => router.push("/highlights")}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div className="min-w-0">
            <h1 className="page-title truncate">{video.filename}</h1>
            <div className="mt-1 flex items-center gap-2">
              <StatusBadge status={video.status} />
              <span className="text-xs text-muted-foreground">
                {video.moment_count} moment
                {video.moment_count === 1 ? "" : "s"}
              </span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReanalyze}
            disabled={reanalyze.isPending || isActive(video.status)}
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
            Re-analyze
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDelete}
            disabled={del.isPending}
          >
            <Trash2 className="h-3.5 w-3.5 mr-1.5" />
            Delete
          </Button>
        </div>
      </div>

      {video.status === "failed" && (
        <Alert variant="destructive">
          <Info className="h-4 w-4" />
          <AlertTitle>Analysis failed</AlertTitle>
          <AlertDescription>
            {video.error || "The pipeline did not complete."} Try re-analyzing.
          </AlertDescription>
        </Alert>
      )}

      {ready && !video.ai_summaries && (
        <Alert>
          <Sparkles className="h-4 w-4" />
          <AlertTitle>AI summaries are off</AlertTitle>
          <AlertDescription>
            Moments use a templated description. Set{" "}
            <code className="font-mono">ANTHROPIC_API_KEY</code> in{" "}
            <code className="font-mono">.env</code> and re-analyze for
            AI-written summaries.
          </AlertDescription>
        </Alert>
      )}

      <AnnotatedPlayer videoId={videoId} ready={!!ready} />

      {isActive(video.status) ? (
        <Card>
          <CardContent className="p-0">
            <EmptyState
              icon={RefreshCw}
              title="Analyzing…"
              description="Detection, tracking, clipping, annotation, and summaries run on the server. This page updates automatically."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="card-title">Moments</h2>
            <div className="relative max-w-xs flex-1">
              <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter moments by description or tag"
                className="pl-8 h-8"
              />
            </div>
          </div>

          {filtered.length === 0 ? (
            <Card>
              <CardContent className="p-0">
                <EmptyState
                  icon={Search}
                  title={query ? "No matching moments" : "No moments detected"}
                  description={
                    query
                      ? "Try a different search term."
                      : "The pipeline did not find any high-activity moments in this clip."
                  }
                />
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {filtered.map((item) => (
                <MomentCard key={item.moment.id} item={item} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
