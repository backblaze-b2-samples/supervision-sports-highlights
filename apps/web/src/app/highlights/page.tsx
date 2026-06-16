import Link from "next/link";
import { Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { HighlightsLibrary } from "@/components/highlights/highlights-library";

export default function HighlightsPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Highlights</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Every clip you&apos;ve analyzed. Each card streams its thumbnail and
            assets straight from Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/upload">
            <Upload className="h-3.5 w-3.5" />
            Upload a clip
          </Link>
        </Button>
      </div>
      <div className="animate-fade-in-up stagger-2">
        <HighlightsLibrary />
      </div>
    </div>
  );
}
