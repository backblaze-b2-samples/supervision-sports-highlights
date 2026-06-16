"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ApiError,
  deleteFile,
  deleteVideo,
  getFiles,
  getFileStats,
  getPipelineStats,
  getPreviewUrl,
  getUploadActivity,
  getVideo,
  getVideoMoments,
  getVideoPlayback,
  getVideos,
  reanalyzeVideo,
  searchMoments,
} from "@/lib/api-client";
import {
  ACTIVE_VIDEO_STATUSES,
  type FileMetadata,
  type Video,
  type VideoSummary,
} from "@supervision-sports-highlights/shared";

// Single source of truth for query keys. Keep these tightly scoped so that
// invalidating "files" doesn't blow away unrelated caches, and so an IDE
// "find usages" of `qk.files` reveals every consumer.
export const qk = {
  all: ["b2"] as const,
  files: (prefix?: string, limit?: number) =>
    [...qk.all, "files", prefix ?? "", limit ?? 100] as const,
  stats: () => [...qk.all, "stats"] as const,
  uploadActivity: (days: number) =>
    [...qk.all, "stats", "activity", days] as const,
  preview: (key: string) => [...qk.all, "preview", key] as const,
  pipelineStats: () => [...qk.all, "pipeline-stats"] as const,
  videos: () => [...qk.all, "videos"] as const,
  video: (id: string) => [...qk.all, "video", id] as const,
  videoMoments: (id: string) => [...qk.all, "video", id, "moments"] as const,
  videoPlayback: (id: string) => [...qk.all, "video", id, "playback"] as const,
  search: (q: string) => [...qk.all, "search", q] as const,
};

// While any analysis job is in flight, poll every 4s; stop once everything is
// terminal (ready/failed). Shared by the list, detail, and dashboard views.
const POLL_MS = 4000;

function anyActive(videos: { status: string }[] | undefined): boolean {
  return !!videos?.some((v) =>
    (ACTIVE_VIDEO_STATUSES as string[]).includes(v.status)
  );
}

export function useFiles(prefix = "", limit = 100) {
  return useQuery<FileMetadata[], ApiError>({
    queryKey: qk.files(prefix, limit),
    queryFn: () => getFiles(prefix, limit),
  });
}

export function useFileStats() {
  return useQuery({
    queryKey: qk.stats(),
    queryFn: getFileStats,
  });
}

export function useUploadActivity(days = 7) {
  return useQuery({
    queryKey: qk.uploadActivity(days),
    queryFn: () => getUploadActivity(days),
  });
}

// Presigned preview URL — only fetched when `enabled` is true (e.g., when
// the dialog opens for a specific file). Kept short-lived (60s) because
// the URL itself has a presigned expiry and is cheap to regenerate.
export function usePreviewUrl(key: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: qk.preview(key ?? ""),
    queryFn: () => getPreviewUrl(key as string),
    enabled: enabled && !!key,
    staleTime: 60_000,
  });
}

export function useDeleteFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (fileKey: string) => deleteFile(fileKey),
    // After delete, blow away every cached file list + stats. Cheap and
    // correct — the dashboard re-fetches lazily as components remount.
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.all });
    },
  });
}

// --- Sports highlights pipeline ---

export function usePipelineStats() {
  return useQuery({
    queryKey: qk.pipelineStats(),
    queryFn: getPipelineStats,
    refetchInterval: (q) => (anyActive(q.state.data?.recent) ? POLL_MS : false),
  });
}

export function useVideos() {
  return useQuery<VideoSummary[], ApiError>({
    queryKey: qk.videos(),
    queryFn: getVideos,
    refetchInterval: (q) => (anyActive(q.state.data) ? POLL_MS : false),
  });
}

export function useVideo(id: string) {
  return useQuery<Video, ApiError>({
    queryKey: qk.video(id),
    queryFn: () => getVideo(id),
    enabled: !!id,
    refetchInterval: (q) =>
      anyActive(q.state.data ? [q.state.data] : undefined) ? POLL_MS : false,
  });
}

// Moments (with presigned clip/thumb URLs) are only meaningful once the video
// is ready, so callers pass `enabled` keyed on status.
export function useVideoMoments(id: string, enabled: boolean) {
  return useQuery({
    queryKey: qk.videoMoments(id),
    queryFn: () => getVideoMoments(id),
    enabled: enabled && !!id,
    staleTime: 5 * 60_000,
  });
}

export function useVideoPlayback(id: string, enabled: boolean) {
  return useQuery({
    queryKey: qk.videoPlayback(id),
    queryFn: () => getVideoPlayback(id),
    enabled: enabled && !!id,
    staleTime: 5 * 60_000,
  });
}

export function useSearchMoments(query: string) {
  return useQuery({
    queryKey: qk.search(query),
    queryFn: () => searchMoments(query),
    enabled: query.trim().length > 0,
  });
}

export function useDeleteVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteVideo(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}

export function useReanalyzeVideo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => reanalyzeVideo(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.all }),
  });
}
