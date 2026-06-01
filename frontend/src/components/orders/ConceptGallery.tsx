"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { CONCEPT_ANGLE_LABELS, type ProjectAsset } from "@/types";

interface Props {
  images: ProjectAsset[];
  onApprove: (comment?: string) => void;
  onReject: (comment: string) => void;
  isLoading?: boolean;
  canApprove?: boolean;
}

// "concept_front.png" -> "front"
function angleOf(asset: ProjectAsset): string {
  const m = asset.filename.match(/concept_(\w+)\./);
  return m ? m[1] : "";
}

export function ConceptGallery({
  images,
  onApprove,
  onReject,
  isLoading = false,
  canApprove = false,
}: Props) {
  const [zoom, setZoom] = useState<ProjectAsset | null>(null);
  const [comment, setComment] = useState("");
  const [rejectError, setRejectError] = useState<string | null>(null);

  function handleReject() {
    if (!comment.trim()) {
      setRejectError("Explique o que ajustar para gerar um novo conceito.");
      return;
    }
    setRejectError(null);
    onReject(comment.trim());
  }

  return (
    <div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {images.map((img) => {
          const angle = angleOf(img);
          return (
            <button
              key={img.id}
              type="button"
              onClick={() => setZoom(img)}
              className="group overflow-hidden rounded-lg border text-left"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={img.storage_url}
                alt={`Conceito ${CONCEPT_ANGLE_LABELS[angle] ?? angle}`}
                className="aspect-square w-full object-cover transition-transform group-hover:scale-105"
              />
              <span className="block px-2 py-1 text-center text-xs text-muted-foreground">
                {CONCEPT_ANGLE_LABELS[angle] ?? angle}
              </span>
            </button>
          );
        })}
      </div>

      {canApprove && (
        <div className="mt-6 space-y-3">
          <Textarea
            placeholder="Comentário (opcional ao aprovar, obrigatório ao rejeitar)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            rows={2}
          />
          {rejectError && <p className="text-sm text-destructive">{rejectError}</p>}
          <div className="flex flex-wrap gap-2">
            <Button
              onClick={() => onApprove(comment.trim() || undefined)}
              disabled={isLoading}
              className="bg-green-600 hover:bg-green-700"
            >
              {isLoading ? "Processando..." : "Aprovar conceito e gerar modelo 3D"}
            </Button>
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={isLoading}
            >
              Rejeitar e gerar novo conceito
            </Button>
          </div>
        </div>
      )}

      {zoom && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-6"
          onClick={() => setZoom(null)}
        >
          <div className="max-h-full max-w-2xl" onClick={(e) => e.stopPropagation()}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={zoom.storage_url}
              alt={`Conceito ${CONCEPT_ANGLE_LABELS[angleOf(zoom)] ?? ""}`}
              className="max-h-[80vh] w-full rounded-lg object-contain"
            />
            <p className="mt-2 text-center text-sm text-white">
              {CONCEPT_ANGLE_LABELS[angleOf(zoom)] ?? angleOf(zoom)} — clique para fechar
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
