import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { MeshValidationReport } from "@/types";

export function MeshReportCard({ report }: { report: MeshValidationReport }) {
  const bb = report.bounding_box_mm;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Validação da malha</span>
          {report.is_valid ? (
            <span className="text-sm font-medium text-green-700">✅ Aprovado</span>
          ) : (
            <span className="text-sm font-medium text-red-700">❌ Problemas</span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="grid grid-cols-2 gap-2">
          <Metric label="Vértices" value={report.vertex_count.toLocaleString("pt-BR")} />
          <Metric label="Faces" value={report.face_count.toLocaleString("pt-BR")} />
          <Metric
            label="Dimensões (mm)"
            value={`${bb.x} × ${bb.y} × ${bb.z}`}
          />
          <Metric label="Volume (cm³)" value={String(report.estimated_volume_cm3)} />
          <Metric label="Manifold" value={report.is_manifold ? "Sim" : "Não"} />
          <Metric label="Precisa suportes" value={report.needs_supports ? "Sim" : "Não"} />
        </div>

        {report.issues.length > 0 && (
          <div>
            <p className="font-medium text-red-700">Problemas</p>
            <ul className="list-disc pl-5 text-muted-foreground">
              {report.issues.map((i, idx) => (
                <li key={idx}>{i}</li>
              ))}
            </ul>
          </div>
        )}

        {report.warnings.length > 0 && (
          <div>
            <p className="font-medium text-amber-700">Avisos</p>
            <ul className="list-disc pl-5 text-muted-foreground">
              {report.warnings.map((w, idx) => (
                <li key={idx}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {report.repair_attempted && (
          <p className="text-xs text-muted-foreground">
            Reparo automático: {report.repair_succeeded ? "bem-sucedido ✓" : "não resolveu"}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value}</p>
    </div>
  );
}
