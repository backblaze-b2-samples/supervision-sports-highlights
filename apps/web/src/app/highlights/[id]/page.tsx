import { AnalysisDetail } from "@/components/highlights/analysis-detail";

export default async function HighlightDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="animate-fade-in">
      <AnalysisDetail videoId={id} />
    </div>
  );
}
