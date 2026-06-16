import Link from "next/link";
import { Upload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PipelineStatsCards } from "@/components/dashboard/pipeline-stats-cards";
import { RecentAnalysesTable } from "@/components/dashboard/recent-analyses-table";
import { UploadChart } from "@/components/dashboard/upload-chart";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div className="animate-fade-in border-b border-border pb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="text-sm text-muted-foreground mt-1.5">
            Your sports-highlights pipeline at a glance — every video, moment,
            and clip is stored on Backblaze B2.
          </p>
        </div>
        <Button asChild size="sm" className="h-8">
          <Link href="/upload">
            <Upload className="h-3.5 w-3.5" />
            Upload a clip
          </Link>
        </Button>
      </div>
      <PipelineStatsCards />
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="animate-fade-in-up stagger-3">
          <UploadChart />
        </div>
        <div className="animate-fade-in-up stagger-4">
          <RecentAnalysesTable />
        </div>
      </div>
    </div>
  );
}
