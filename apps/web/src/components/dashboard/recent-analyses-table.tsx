"use client";

import Link from "next/link";
import { ArrowRight, Inbox } from "lucide-react";
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { StatusBadge } from "@/components/highlights/status-badge";
import { usePipelineStats } from "@/lib/queries";
import { formatDate } from "@/lib/utils";

export function RecentAnalysesTable() {
  const { data, isLoading, error, refetch } = usePipelineStats();
  const recent = data?.recent ?? [];

  return (
    <Card>
      <CardHeader className="border-b border-border py-4 px-5">
        <CardTitle className="card-title">Recent Analyses</CardTitle>
        <CardAction className="self-center">
          <Link
            href="/highlights"
            className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            View all
            <ArrowRight className="h-3 w-3" />
          </Link>
        </CardAction>
      </CardHeader>
      <CardContent className="p-0">
        {isLoading ? (
          <div className="p-4 space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        ) : error ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : recent.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="No analyses yet"
            description="Upload a sports clip to start the pipeline."
          />
        ) : (
          <Table className="table-fixed">
            <TableHeader>
              <TableRow className="bg-muted/40 hover:bg-muted/40">
                <TableHead className="w-[44%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Clip
                </TableHead>
                <TableHead className="w-[14%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Moments
                </TableHead>
                <TableHead className="w-[22%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Updated
                </TableHead>
                <TableHead className="w-[20%] text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Status
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recent.map((v) => (
                <TableRow key={v.id} className="table-row-hover">
                  <TableCell className="font-medium">
                    <Link
                      href={`/highlights/${v.id}`}
                      className="truncate block hover:underline"
                    >
                      {v.filename}
                    </Link>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground tabular-nums">
                    {v.moment_count}
                  </TableCell>
                  <TableCell className="text-muted-foreground whitespace-nowrap">
                    {formatDate(v.updated_at)}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
                    <StatusBadge status={v.status} />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
