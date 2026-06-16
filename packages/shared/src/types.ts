export type FileStatus = "uploading" | "complete" | "error";

export interface FileMetadata {
  key: string;
  filename: string;
  folder: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
}

export interface FileMetadataDetail {
  filename: string;
  size_bytes: number;
  size_human: string;
  mime_type: string;
  extension: string;
  md5: string;
  sha256: string;
  uploaded_at: string;
  // Video-specific (populated by the CV pipeline, not at upload time).
  duration_seconds: number | null;
  codec: string | null;
  bitrate: number | null;
}

export interface FileUploadResponse {
  key: string;
  filename: string;
  size_bytes: number;
  size_human: string;
  content_type: string;
  uploaded_at: string;
  url: string | null;
  metadata: FileMetadataDetail | null;
}

export interface DailyUploadCount {
  date: string;
  uploads: number;
}

export interface UploadStats {
  total_files: number;
  total_size_bytes: number;
  total_size_human: string;
  uploads_today: number;
  total_downloads: number;
}

// --- Sports highlights pipeline ---

export type VideoStatus =
  | "uploaded"
  | "probing"
  | "detecting"
  | "clipping"
  | "annotating"
  | "summarizing"
  | "ready"
  | "failed";

export const ACTIVE_VIDEO_STATUSES: VideoStatus[] = [
  "uploaded",
  "probing",
  "detecting",
  "clipping",
  "annotating",
  "summarizing",
];

export interface Moment {
  id: number;
  start_s: number;
  end_s: number;
  score: number;
  peak_person_count: number;
  unique_track_ids: number;
  ball_present: boolean;
  detection_count: number;
  thumb_key: string | null;
  clip_key: string | null;
  summary: string;
  description: string;
  tags: string[];
}

export interface Video {
  id: string;
  filename: string;
  status: VideoStatus;
  source_key: string;
  annotated_key: string | null;
  error: string | null;
  duration_seconds: number | null;
  fps: number | null;
  width: number | null;
  height: number | null;
  moments: Moment[];
  moment_count: number;
  ai_summaries: boolean;
  created_at: string;
  updated_at: string;
}

export interface VideoSummary {
  id: string;
  filename: string;
  status: VideoStatus;
  moment_count: number;
  duration_seconds: number | null;
  thumb_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface MomentPlayback {
  moment: Moment;
  clip_url: string | null;
  thumb_url: string | null;
}

export interface SearchHit {
  video_id: string;
  video_filename: string;
  moment: Moment;
}

export interface PipelineStats {
  videos_analyzed: number;
  highlights_generated: number;
  moments_detected: number;
  footage_minutes: number;
  recent: VideoSummary[];
}
