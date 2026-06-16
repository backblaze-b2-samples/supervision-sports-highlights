"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { Accept, FileRejection } from "react-dropzone";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dropzone } from "./dropzone";
import { UploadProgress, type UploadItem } from "./upload-progress";
import { uploadVideo } from "@/lib/api-client";
import { humanizeBytes } from "@/lib/utils";
import { qk } from "@/lib/queries";

// The analyzer only accepts video. Keep clips short (≤ ~2 min) — the CV
// pipeline runs locally and is CPU-bound. See README.
const VIDEO_ACCEPT: Accept = {
  "video/mp4": [".mp4"],
  "video/quicktime": [".mov"],
  "video/webm": [".webm"],
};
const MAX_VIDEO_SIZE = 500 * 1024 * 1024; // 500MB

export function UploadForm() {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [uploading, setUploading] = useState(false);
  const router = useRouter();
  const qc = useQueryClient();

  const handleFilesRejected = useCallback((rejections: FileRejection[]) => {
    for (const rejection of rejections) {
      const name = rejection.file.name;
      const errors = rejection.errors.map((e) => {
        if (e.code === "file-too-large") {
          return `exceeds ${humanizeBytes(MAX_VIDEO_SIZE)} limit (${humanizeBytes(
            rejection.file.size
          )})`;
        }
        if (e.code === "file-invalid-type") {
          return "not a supported video (use mp4, mov, or webm)";
        }
        return e.message;
      });
      toast.error(`${name}: ${errors.join(", ")}`);
    }
  }, []);

  const handleFilesSelected = useCallback(
    (files: File[]) => {
      const file = files[0];
      if (!file) return;
      const item: UploadItem = {
        id: `${file.name}-${Date.now()}`,
        file,
        progress: 0,
        status: "uploading",
      };
      setItems([item]);
      setUploading(true);

      uploadVideo(file, (percent) => {
        setItems((prev) =>
          prev.map((i) => (i.id === item.id ? { ...i, progress: percent } : i))
        );
      })
        .then((video) => {
          setItems((prev) =>
            prev.map((i) =>
              i.id === item.id ? { ...i, status: "complete", progress: 100 } : i
            )
          );
          toast.success(
            `${file.name} uploaded — analysis started. Redirecting to Highlights…`
          );
          qc.invalidateQueries({ queryKey: qk.all });
          router.push(`/highlights/${video.id}`);
        })
        .catch((err) => {
          const message = err instanceof Error ? err.message : "Upload failed";
          setItems((prev) =>
            prev.map((i) =>
              i.id === item.id ? { ...i, status: "error", error: message } : i
            )
          );
          toast.error(`Failed to upload ${file.name}: ${message}`);
        })
        .finally(() => setUploading(false));
    },
    [qc, router]
  );

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Upload a sports clip</CardTitle>
      </CardHeader>
      <CardContent className="p-5 space-y-4">
        <Dropzone
          onFilesSelected={handleFilesSelected}
          onFilesRejected={handleFilesRejected}
          disabled={uploading}
          accept={VIDEO_ACCEPT}
          maxSize={MAX_VIDEO_SIZE}
          multiple={false}
          hint="mp4, mov, or webm — keep it short (≤ ~2 min) for a fast demo run"
        />
        <UploadProgress items={items} />
      </CardContent>
    </Card>
  );
}
