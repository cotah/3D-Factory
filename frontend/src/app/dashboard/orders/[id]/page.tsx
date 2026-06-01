"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { AxiosError } from "axios";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ordersApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { StatusBadge } from "@/components/orders/StatusBadge";
import { OrderStatusTimeline } from "@/components/orders/OrderStatusTimeline";
import { AIBriefCard } from "@/components/orders/AIBriefCard";
import { ConceptGallery } from "@/components/orders/ConceptGallery";
import { MeshReportCard } from "@/components/orders/MeshReportCard";
import type { OrderDetail } from "@/types";

// The 3D viewer touches the DOM/WebGL, so load it client-only.
const ThreeDViewer = dynamic(
  () => import("@/components/3d/ThreeDViewer").then((m) => m.ThreeDViewer),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[400px] items-center justify-center rounded-lg bg-[#1a1a1a] text-sm text-white/70">
        Inicializando visualizador 3D...
      </div>
    ),
  },
);

// Statuses where a background job may advance the order; poll until it leaves.
const POLLING_STATUSES = ["validating_mesh", "generating_3d"];

function OrderDetailContent() {
  const params = useParams();
  const router = useRouter();
  const orderId = Number(params.id);

  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [finalComment, setFinalComment] = useState("");

  // Track whether an action is in flight so polling doesn't race it.
  const actionInFlight = useRef(false);

  const load = useCallback(async () => {
    try {
      const detail = await ordersApi.getDetail(orderId);
      setOrder(detail);
    } catch {
      setNotFound(true);
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    if (orderId) void load();
  }, [orderId, load]);

  // Polling: while the order is in a transient state, refresh every 3s.
  useEffect(() => {
    if (!order || !POLLING_STATUSES.includes(order.status)) return;
    const interval = setInterval(async () => {
      if (actionInFlight.current) return;
      try {
        const updated = await ordersApi.getDetail(orderId);
        setOrder(updated);
      } catch {
        /* keep last known state */
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [order?.status, orderId, order]);

  function describeError(err: unknown): string {
    return err instanceof AxiosError
      ? (err.response?.data?.detail as string) ?? "Ocorreu um erro"
      : "Ocorreu um erro";
  }

  async function runAction(fn: () => Promise<OrderDetail>) {
    setActionLoading(true);
    setActionError(null);
    actionInFlight.current = true;
    try {
      setOrder(await fn());
    } catch (err) {
      setActionError(describeError(err));
    } finally {
      actionInFlight.current = false;
      setActionLoading(false);
    }
  }

  const handleGenerateBrief = () =>
    runAction(() => ordersApi.generateBrief(orderId));
  const handleApproveConcept = (comment?: string) =>
    runAction(() => ordersApi.approveConcept(orderId, { approved: true, comment }));
  const handleRejectConcept = (comment: string) =>
    runAction(async () => {
      await ordersApi.approveConcept(orderId, { approved: false, comment });
      return ordersApi.generateConcept(orderId);
    });
  const handleGenerate3D = () => runAction(() => ordersApi.generate3D(orderId));
  const handleApproveFinal = () =>
    runAction(() =>
      ordersApi.approveFinal(orderId, {
        approved: true,
        comment: finalComment.trim() || undefined,
      }),
    );
  const handleRejectFinal = () =>
    runAction(() =>
      ordersApi.approveFinal(orderId, {
        approved: false,
        comment: finalComment.trim() || undefined,
      }),
    );

  if (loading) {
    return <p className="px-6 py-10 text-muted-foreground">Carregando...</p>;
  }
  if (notFound || !order) {
    return (
      <div className="px-6 py-10">
        <p className="text-muted-foreground">Pedido não encontrado.</p>
        <Button className="mt-4" variant="outline" onClick={() => router.push("/dashboard")}>
          Voltar
        </Button>
      </div>
    );
  }

  const conceptImages = order.assets.filter((a) => a.type === "concept_image");
  const referenceAssets = order.assets.filter((a) => a.type !== "concept_image" && a.type !== "model_3d");
  const modelAssets = order.assets.filter((a) => a.type === "model_3d");
  const latestModel = modelAssets[modelAssets.length - 1];
  const generatingConcept =
    order.status === "waiting_brief" || order.status === "generating_concept";
  const generating3d =
    order.status === "validating_mesh" || (actionLoading && order.status === "generating_3d");

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <Button variant="ghost" className="mb-4 px-0" onClick={() => router.push("/dashboard")}>
        ← Voltar
      </Button>

      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">{order.title}</h1>
        <StatusBadge status={order.status} />
      </div>

      {actionError && (
        <p className="mb-4 rounded-md bg-red-50 px-3 py-2 text-sm text-destructive">
          {actionError}
        </p>
      )}

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Detalhes</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {order.description && <p>{order.description}</p>}
            <DetailRow label="Categoria" value={order.category} />
            <DetailRow label="Material" value={order.material} />
            <DetailRow label="Tamanho" value={order.size} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Progresso</CardTitle>
          </CardHeader>
          <CardContent>
            <OrderStatusTimeline status={order.status} />
          </CardContent>
        </Card>
      </div>

      {/* Brief generation (draft) */}
      {order.status === "draft" && (
        <div className="mt-6">
          <Button onClick={handleGenerateBrief} disabled={actionLoading}>
            {actionLoading ? "Gerando briefing e conceito..." : "Gerar Briefing com IA"}
          </Button>
        </div>
      )}

      {generatingConcept && <Spinner label="Gerando conceito visual..." />}

      {order.brief && (
        <div className="mt-6">
          <AIBriefCard brief={order.brief} />
        </div>
      )}

      {conceptImages.length > 0 && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Imagens Conceituais</CardTitle>
          </CardHeader>
          <CardContent>
            <ConceptGallery
              images={conceptImages}
              onApprove={handleApproveConcept}
              onReject={handleRejectConcept}
              isLoading={actionLoading}
              canApprove={order.status === "waiting_concept_approval"}
            />
          </CardContent>
        </Card>
      )}

      {/* Generate 3D action */}
      {order.status === "generating_3d" && !actionLoading && (
        <div className="mt-6">
          <Button onClick={handleGenerate3D}>Gerar Modelo 3D</Button>
          <p className="mt-2 text-xs text-muted-foreground">
            Envia as imagens aprovadas para o TRELLIS.2 e valida a malha.
          </p>
        </div>
      )}

      {order.status === "ai_revision_required" && (
        <div className="mt-6 rounded-md bg-orange-50 px-4 py-3">
          <p className="text-sm text-orange-800">
            A última tentativa falhou. Tentativa {order.ai_attempts} de 3.
          </p>
          <Button className="mt-3" onClick={handleGenerate3D} disabled={actionLoading}>
            {actionLoading ? "Gerando..." : "Tentar Novamente"}
          </Button>
        </div>
      )}

      {generating3d && <Spinner label="Gerando modelo 3D..." />}

      {/* 3D viewer + mesh report */}
      {latestModel && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Modelo 3D</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ThreeDViewer modelUrl={latestModel.storage_url} height={400} />
            {order.mesh_report && <MeshReportCard report={order.mesh_report} />}
          </CardContent>
        </Card>
      )}

      {/* Final approval */}
      {order.status === "waiting_final_approval" && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Aprovação do modelo</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              placeholder="Comentário (opcional)"
              value={finalComment}
              onChange={(e) => setFinalComment(e.target.value)}
              rows={2}
            />
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={handleApproveFinal}
                disabled={actionLoading}
                className="bg-green-600 hover:bg-green-700"
              >
                {actionLoading ? "Processando..." : "Aprovar Modelo"}
              </Button>
              <Button variant="destructive" onClick={handleRejectFinal} disabled={actionLoading}>
                Pedir Revisão
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {order.status === "designer_required" && (
        <div className="mt-6 rounded-md bg-purple-50 px-4 py-3 text-sm text-purple-800">
          🎨 Pedido encaminhado para um designer humano. Você será avisado quando o
          modelo estiver pronto.
        </div>
      )}

      {order.status === "ready_for_slicing" && (
        <div className="mt-6 rounded-md bg-green-50 px-4 py-3 text-sm text-green-800">
          ✓ Modelo aprovado! Em preparação para impressão.
        </div>
      )}

      {/* Reference files */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Arquivos de referência ({referenceAssets.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {referenceAssets.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nenhum arquivo enviado ainda.</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {referenceAssets.map((asset) => (
                <li key={asset.id} className="flex justify-between">
                  <span>{asset.filename}</span>
                  <span className="text-muted-foreground">
                    {(asset.size_bytes / 1024).toFixed(1)} KB
                  </span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </main>
  );
}

function Spinner({ label }: { label: string }) {
  return (
    <div className="mt-6 flex items-center gap-3 rounded-md bg-blue-50 px-4 py-3 text-sm text-blue-800">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-300 border-t-blue-700" />
      {label}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: string | null }) {
  if (!value) return null;
  return (
    <p>
      <span className="text-muted-foreground">{label}:</span> {value}
    </p>
  );
}

export default function OrderDetailPage() {
  return (
    <ProtectedRoute>
      <OrderDetailContent />
    </ProtectedRoute>
  );
}
