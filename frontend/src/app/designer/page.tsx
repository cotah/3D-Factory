"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/components/AuthProvider";
import { designerApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  COMPLEXITY_COLORS,
  COMPLEXITY_LABELS,
  type DesignerTask,
} from "@/types";
import { cn } from "@/lib/utils";

const TASK_STATUS_LABELS: Record<string, string> = {
  open: "Aberta",
  in_progress: "Em andamento",
  submitted: "Enviada",
  closed: "Concluída",
};

function DesignerDashboard() {
  const { user, logout } = useAuth();
  const [tasks, setTasks] = useState<DesignerTask[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    designerApi
      .listTasks()
      .then(setTasks)
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Painel do Designer</h1>
          <p className="text-sm text-muted-foreground">
            {user?.full_name || user?.email}
          </p>
        </div>
        <Button variant="outline" onClick={logout}>
          Sair
        </Button>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Carregando tarefas...</p>
      ) : tasks.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            Nenhuma tarefa atribuída a você no momento.
          </CardContent>
        </Card>
      ) : (
        <div className="overflow-hidden rounded-lg border">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-left">
              <tr>
                <th className="px-4 py-2">Referência</th>
                <th className="px-4 py-2">Categoria</th>
                <th className="px-4 py-2">Complexidade</th>
                <th className="px-4 py-2">Prazo</th>
                <th className="px-4 py-2">Status</th>
                <th className="px-4 py-2"></th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => {
                const complexity = task.brief?.complexity ?? "medium";
                return (
                  <tr key={task.id} className="border-t">
                    <td className="px-4 py-3 font-medium">
                      {task.brief?.order_reference ?? `#${task.order_id}`}
                    </td>
                    <td className="px-4 py-3">{task.brief?.category ?? "-"}</td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                          COMPLEXITY_COLORS[complexity] ?? "bg-slate-100",
                        )}
                      >
                        {COMPLEXITY_LABELS[complexity] ?? complexity}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {task.deadline
                        ? new Date(task.deadline).toLocaleDateString("pt-BR")
                        : "-"}
                    </td>
                    <td className="px-4 py-3">
                      {TASK_STATUS_LABELS[task.status] ?? task.status}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link href={`/designer/tasks/${task.id}`}>
                        <Button size="sm" variant="outline">
                          Ver detalhes
                        </Button>
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

export default function DesignerPage() {
  return (
    <ProtectedRoute roles={["designer", "admin"]}>
      <DesignerDashboard />
    </ProtectedRoute>
  );
}
