"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { AxiosError } from "axios";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { designerApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  COMPLEXITY_COLORS,
  COMPLEXITY_LABELS,
  CONCEPT_ANGLE_LABELS,
  type DesignerTask,
  type ProjectAsset,
} from "@/types";
import { cn } from "@/lib/utils";

const ALLOWED_EXT = [".glb", ".obj", ".stl"];
const MAX_MB = 50;

function angleOf(asset: ProjectAsset): string {
  const m = asset.filename.match(/concept_(\w+)\./);
  return m ? m[1] : "";
}

function TaskDetail() {
  const params = useParams();
  const router = useRouter();
  const taskId = Number(params.id);

  const [task, setTask] = useState<DesignerTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setTask(await designerApi.getTask(taskId));
    } catch {
      setNotFound(true);
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    if (taskId) void load();
  }, [taskId, load]);

  function pickFile(f: File | null) {
    setError(null);
    if (!f) {
      setFile(null);
      return;
    }
    const ext = f.name.slice(f.name.lastIndexOf(".")).toLowerCase();
    if (!ALLOWED_EXT.includes(ext)) {
      setError(`Formato inválido. Use: ${ALLOWED_EXT.join(", ")}`);
      return;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      setError(`Arquivo excede ${MAX_MB}MB.`);
      return;
    }
    setFile(f);
  }

  async function onUpload() {
    if (!task || !file) return;
    setUploading(true);
    setError(null);
    try {
      await designerApi.uploadFinalModel(task.order_id, file);
      setSuccess(true);
      setFile(null);
      await load();
    } catch (err) {
      setError(
        err instanceof AxiosError
          ? (err.response?.data?.detail as string) ?? "Falha no upload"
          : "Falha no upload",
      );
    } finally {
      setUploading(false);
    }
  }

  if (loading) {
    return <p className="px-6 py-10 text-muted-foreground">Carregando...</p>;
  }
  if (notFound || !task) {
    return (
      <div className="px-6 py-10">
        <p className="text-muted-foreground">Tarefa não encontrada.</p>
        <Button className="mt-4" variant="outline" onClick={() => router.push("/designer")}>
          Voltar
        </Button>
      </div>
    );
  }

  const brief = task.brief;
  const complexity = brief?.complexity ?? "medium";
  const submitted = task.status === "submitted" || !!task.final_model_url;

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Button variant="ghost" className="mb-4 px-0" onClick={() => router.push("/designer")}>
        ← Voltar
      </Button>

      {/* Section 1: technical brief */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Briefing técnico — {brief?.order_reference}</CardTitle>
            <span
              className={cn(
                "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
                COMPLEXITY_COLORS[complexity] ?? "bg-slate-100",
              )}
            >
              {COMPLEXITY_LABELS[complexity] ?? complexity}
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <p className="text-base font-medium">{brief?.title}</p>
          {brief?.technical_summary && <p>{brief.technical_summary}</p>}
          <div className="grid grid-cols-2 gap-2">
            <Info label="Categoria" value={brief?.category} />
            <Info label="Tamanho" value={brief?.size} />
            <Info label="Cores" value={brief?.colors} />
            <Info label="Material" value={brief?.material} />
          </div>
          {brief?.model_3d_prompt && (
            <div>
              <p className="font-medium">Prompt 3D sugerido</p>
              <p className="text-muted-foreground">{brief.model_3d_prompt}</p>
            </div>
          )}
          {brief && brief.risks.length > 0 && (
            <ListBlock title="Riscos" items={brief.risks} />
          )}
          {brief && brief.print_alerts.length > 0 && (
            <ListBlock title="Alertas de impressão" items={brief.print_alerts} />
          )}
          <div className="rounded-md bg-slate-50 px-3 py-2 text-muted-foreground">
            {brief?.instructions}
          </div>
        </CardContent>
      </Card>

      {/* Section 2: approved concept images */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Imagens conceituais aprovadas</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {task.concept_images.map((img) => (
              <div key={img.id} className="overflow-hidden rounded-lg border">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={img.storage_url}
                  alt={`Conceito ${angleOf(img)}`}
                  className="aspect-square w-full object-cover"
                />
                <span className="block px-2 py-1 text-center text-xs text-muted-foreground">
                  {CONCEPT_ANGLE_LABELS[angleOf(img)] ?? angleOf(img)}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Section 3: upload */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Enviar modelo 3D</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {submitted && (
            <p className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-800">
              ✓ Modelo enviado. O cliente fará a aprovação final.
            </p>
          )}
          <div
            className="cursor-pointer rounded-lg border-2 border-dashed p-6 text-center text-sm text-muted-foreground hover:bg-accent"
            onClick={() => fileInput.current?.click()}
          >
            {file ? (
              <span className="font-medium text-foreground">{file.name}</span>
            ) : (
              <>Clique para escolher um arquivo GLB, OBJ ou STL (máx {MAX_MB}MB)</>
            )}
          </div>
          <input
            ref={fileInput}
            type="file"
            accept=".glb,.obj,.stl"
            className="hidden"
            onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
          {success && !error && (
            <p className="text-sm text-green-700">Upload concluído com sucesso.</p>
          )}
          <Button onClick={onUpload} disabled={!file || uploading}>
            {uploading ? "Enviando..." : "Enviar modelo"}
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}

function Info({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium">{value || "-"}</p>
    </div>
  );
}

function ListBlock({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="font-medium">{title}</p>
      <ul className="list-disc pl-5 text-muted-foreground">
        {items.map((it, i) => (
          <li key={i}>{it}</li>
        ))}
      </ul>
    </div>
  );
}

export default function DesignerTaskPage() {
  return (
    <ProtectedRoute roles={["designer", "admin"]}>
      <TaskDetail />
    </ProtectedRoute>
  );
}
