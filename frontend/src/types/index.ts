// Shared TypeScript types mirroring the backend models, plus UI metadata
// (status labels and colors) used across the order components.

export type UserRole = "customer" | "admin" | "designer" | "print_partner";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export type OrderStatus =
  | "draft"
  | "waiting_brief"
  | "generating_concept"
  | "waiting_concept_approval"
  | "generating_3d"
  | "validating_mesh"
  | "ai_revision_required"
  | "designer_required"
  | "waiting_final_approval"
  | "ready_for_slicing"
  | "slicing"
  | "ready_to_print"
  | "printing"
  | "post_processing"
  | "shipped"
  | "completed"
  | "cancelled";

export interface Order {
  id: number;
  user_id: number;
  title: string;
  description: string;
  category: string | null;
  size: string | null;
  colors: string | null;
  material: string | null;
  deadline: string | null;
  notes: string | null;
  status: OrderStatus;
  ai_attempts: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectAsset {
  id: number;
  order_id: number;
  type: string;
  filename: string;
  storage_url: string;
  content_type: string | null;
  size_bytes: number;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ProductionBrief {
  technical_summary: string;
  image_prompt: string;
  model_3d_prompt: string;
  complexity: string;
  designer_probability: number;
  risks: string[];
  print_alerts: string[];
  estimated_price_range: { min: number; max: number };
}

export interface CustomerApproval {
  id: number;
  order_id: number;
  stage: string;
  status: string;
  comment: string | null;
  created_at: string;
}

export interface MeshValidationReport {
  is_valid: boolean;
  is_manifold: boolean;
  vertex_count: number;
  face_count: number;
  bounding_box_mm: { x: number; y: number; z: number };
  estimated_volume_cm3: number;
  needs_supports: boolean;
  has_flat_base: boolean;
  issues: string[];
  warnings: string[];
  repair_attempted: boolean;
  repair_succeeded: boolean;
}

// Rich order payload returned by GET /orders/{id} and the AI actions.
export interface OrderDetail extends Order {
  ai_brief_json: string | null;
  complexity: string | null;
  brief: ProductionBrief | null;
  assets: ProjectAsset[];
  approvals: CustomerApproval[];
  mesh_report: MeshValidationReport | null;
}

// Friendly Portuguese labels for the 6 concept angles (derived from filename).
export const CONCEPT_ANGLE_LABELS: Record<string, string> = {
  front: "Frontal",
  back: "Traseira",
  left: "Lateral Esq.",
  right: "Lateral Dir.",
  diagonal: "Diagonal",
  top: "Topo",
};

export const COMPLEXITY_LABELS: Record<string, string> = {
  simple: "Simples",
  medium: "Média",
  complex: "Complexa",
};

export const COMPLEXITY_COLORS: Record<string, string> = {
  simple: "bg-green-100 text-green-800",
  medium: "bg-amber-100 text-amber-800",
  complex: "bg-red-100 text-red-700",
};

// Human-readable Portuguese labels for each status.
export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  draft: "Rascunho",
  waiting_brief: "Aguardando briefing",
  generating_concept: "Gerando conceito",
  waiting_concept_approval: "Aguardando aprovação do conceito",
  generating_3d: "Gerando modelo 3D",
  validating_mesh: "Validando malha",
  ai_revision_required: "Revisão da IA necessária",
  designer_required: "Designer necessário",
  waiting_final_approval: "Aguardando aprovação final",
  ready_for_slicing: "Pronto para fatiamento",
  slicing: "Fatiando",
  ready_to_print: "Pronto para impressão",
  printing: "Imprimindo",
  post_processing: "Pós-processamento",
  shipped: "Enviado",
  completed: "Concluído",
  cancelled: "Cancelado",
};

// Tailwind color classes for each status badge.
export const ORDER_STATUS_COLORS: Record<OrderStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  waiting_brief: "bg-amber-100 text-amber-800",
  generating_concept: "bg-blue-100 text-blue-800",
  waiting_concept_approval: "bg-amber-100 text-amber-800",
  generating_3d: "bg-blue-100 text-blue-800",
  validating_mesh: "bg-indigo-100 text-indigo-800",
  ai_revision_required: "bg-orange-100 text-orange-800",
  designer_required: "bg-purple-100 text-purple-800",
  waiting_final_approval: "bg-amber-100 text-amber-800",
  ready_for_slicing: "bg-cyan-100 text-cyan-800",
  slicing: "bg-cyan-100 text-cyan-800",
  ready_to_print: "bg-teal-100 text-teal-800",
  printing: "bg-teal-100 text-teal-800",
  post_processing: "bg-teal-100 text-teal-800",
  shipped: "bg-green-100 text-green-800",
  completed: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-700",
};

// The happy-path order lifecycle shown in the timeline (terminal/branch
// states like cancelled and designer_required are handled separately).
export const ORDER_LIFECYCLE: OrderStatus[] = [
  "draft",
  "waiting_brief",
  "generating_concept",
  "waiting_concept_approval",
  "generating_3d",
  "validating_mesh",
  "waiting_final_approval",
  "ready_for_slicing",
  "ready_to_print",
  "printing",
  "shipped",
  "completed",
];
