import type {
  DailyUploadCount,
  FileMetadata,
  FileUploadResponse,
  MomentPlayback,
  PipelineStats,
  SearchHit,
  UploadStats,
  Video,
  VideoSummary,
} from "@supervision-sports-highlights/shared";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** Typed API error with HTTP status code for caller-side branching. */
export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }

  /** True for 408, 429, 500, 502, 503, 504 — worth retrying. */
  get isRetryable(): boolean {
    return [408, 429, 500, 502, 503, 504].includes(this.status);
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }

  get isConflict(): boolean {
    return this.status === 409;
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    // Network failure (offline, DNS, CORS, etc.)
    throw new ApiError("Network error — check your connection", 0);
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(
      body.detail || `API error: ${res.status}`,
      res.status,
    );
  }
  return res.json();
}

export async function getHealth() {
  return apiFetch<{ status: string; b2_connected: boolean }>("/health");
}

export async function getFiles(prefix = "", limit = 100) {
  return apiFetch<FileMetadata[]>(
    `/files?prefix=${encodeURIComponent(prefix)}&limit=${limit}`
  );
}

export async function getFileStats() {
  return apiFetch<UploadStats>("/files/stats");
}

export async function getUploadActivity(days = 7) {
  return apiFetch<DailyUploadCount[]>(`/files/stats/activity?days=${days}`);
}

export async function getFile(key: string) {
  return apiFetch<FileMetadata>(`/files/${key}`);
}

export async function getDownloadUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/download`);
}

/** Preview-only presigned URL — does NOT increment the download counter. */
export async function getPreviewUrl(key: string) {
  return apiFetch<{ url: string }>(`/files/${key}/preview`);
}

export async function deleteFile(key: string) {
  return apiFetch<{ deleted: boolean; key: string }>(`/files/${key}`, {
    method: "DELETE",
  });
}

function xhrUpload<T>(
  path: string,
  file: File,
  onProgress?: (percent: number) => void
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append("file", file);

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const body = JSON.parse(xhr.responseText);
          reject(new ApiError(body.detail || `Upload failed: ${xhr.status}`, xhr.status));
        } catch {
          reject(new ApiError(`Upload failed: ${xhr.status}`, xhr.status));
        }
      }
    });

    xhr.addEventListener("error", () =>
      reject(new ApiError("Network error — check your connection", 0)),
    );
    xhr.addEventListener("abort", () =>
      reject(new ApiError("Upload aborted", 0)),
    );

    xhr.open("POST", `${API_BASE}${path}`);
    xhr.send(formData);
  });
}

export function uploadFile(
  file: File,
  onProgress?: (percent: number) => void
): Promise<FileUploadResponse> {
  return xhrUpload<FileUploadResponse>("/upload", file, onProgress);
}

/** Upload a sports video and register it for the CV pipeline. The pipeline
 * runs asynchronously on the server; poll the returned video id for status. */
export function uploadVideo(
  file: File,
  onProgress?: (percent: number) => void
): Promise<Video> {
  return xhrUpload<Video>("/videos", file, onProgress);
}

// --- Sports highlights pipeline ---

export async function getPipelineStats() {
  return apiFetch<PipelineStats>("/videos/stats");
}

export async function getVideos() {
  return apiFetch<VideoSummary[]>("/videos");
}

export async function getVideo(id: string) {
  return apiFetch<Video>(`/videos/${id}`);
}

export async function getVideoPlayback(id: string) {
  return apiFetch<{ url: string }>(`/videos/${id}/playback`);
}

export async function getVideoMoments(id: string) {
  return apiFetch<MomentPlayback[]>(`/videos/${id}/moments`);
}

export async function reanalyzeVideo(id: string) {
  return apiFetch<Video>(`/videos/${id}/reanalyze`, { method: "POST" });
}

export async function deleteVideo(id: string) {
  return apiFetch<{ deleted: boolean; id: string; objects_removed: number }>(
    `/videos/${id}`,
    { method: "DELETE" }
  );
}

export async function searchMoments(query: string) {
  return apiFetch<SearchHit[]>(`/search?q=${encodeURIComponent(query)}`);
}
