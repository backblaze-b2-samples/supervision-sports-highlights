"use client";

import { Clapperboard, Film, Sparkles, Clock } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ui/error-state";
import { usePipelineStats } from "@/lib/queries";

export function PipelineStatsCards() {
  const { data: stats, isLoading, error, refetch } = usePipelineStats();

  if (error) {
    return (
      <Card>
        <CardContent className="p-0">
          <ErrorState error={error} onRetry={() => refetch()} />
        </CardContent>
      </Card>
    );
  }

  const cards = [
    {
      title: "Videos Analyzed",
      value: stats?.videos_analyzed ?? 0,
      icon: Film,
    },
    {
      title: "Highlights Generated",
      value: stats?.highlights_generated ?? 0,
      icon: Clapperboard,
    },
    {
      title: "Moments Detected",
      value: stats?.moments_detected ?? 0,
      icon: Sparkles,
    },
    {
      title: "Footage Processed",
      value: `${stats?.footage_minutes ?? 0} min`,
      icon: Clock,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card, i) => (
        <Card
          key={card.title}
          className={`card-hover animate-fade-in-up stagger-${i + 1}`}
        >
          <CardHeader className="flex flex-row items-center justify-between pt-4 pb-2 px-4 space-y-0">
            <CardTitle className="text-xs font-semibold text-muted-foreground">
              {card.title}
            </CardTitle>
            <div className="stat-icon-wrap">
              <card.icon className="h-4 w-4" />
            </div>
          </CardHeader>
          <CardContent className="pb-5 px-4">
            {isLoading ? (
              <Skeleton className="h-8 w-24" />
            ) : (
              <div className="stat-value">{card.value}</div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
