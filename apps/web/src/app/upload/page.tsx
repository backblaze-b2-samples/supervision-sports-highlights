import { UploadForm } from "@/components/upload/upload-form";

export default function UploadPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5">
        <h1 className="page-title">Upload</h1>
        <p className="text-sm text-muted-foreground mt-1.5">
          Drop a sports clip to analyze. We detect the action, cut highlight
          clips, render a Supervision-annotated video, and write AI summaries —
          all stored on Backblaze B2.
        </p>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <UploadForm />
      </div>
    </div>
  );
}
