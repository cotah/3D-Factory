import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { COMPLEXITY_COLORS, COMPLEXITY_LABELS, type ProductionBrief } from "@/types";

export function AIBriefCard({ brief }: { brief: ProductionBrief }) {
  const complexity = brief.complexity ?? "medium";

  return (
    <Card className="border-l-4 border-l-indigo-500">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <span>🤖 Briefing da IA</span>
          </CardTitle>
          <span
            className={cn(
              "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
              COMPLEXITY_COLORS[complexity] ?? "bg-slate-100 text-slate-700",
            )}
          >
            {COMPLEXITY_LABELS[complexity] ?? complexity}
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <p>{brief.technical_summary}</p>

        <div className="rounded-md bg-indigo-50 px-4 py-3">
          <p className="text-xs text-muted-foreground">Faixa de preço estimada</p>
          <p className="text-lg font-semibold text-indigo-900">
            R$ {brief.estimated_price_range.min} – R$ {brief.estimated_price_range.max}
          </p>
        </div>

        {brief.risks.length > 0 && (
          <details className="rounded-md border px-3 py-2">
            <summary className="cursor-pointer font-medium">
              Riscos ({brief.risks.length})
            </summary>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
              {brief.risks.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </details>
        )}

        {brief.print_alerts.length > 0 && (
          <details className="rounded-md border px-3 py-2">
            <summary className="cursor-pointer font-medium">
              Alertas de impressão ({brief.print_alerts.length})
            </summary>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted-foreground">
              {brief.print_alerts.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </details>
        )}
      </CardContent>
    </Card>
  );
}
