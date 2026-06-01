"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { useAuth } from "@/components/AuthProvider";
import { ordersApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/orders/StatusBadge";
import type { Order } from "@/types";

function DashboardContent() {
  const { user, logout } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    ordersApi
      .list()
      .then(setOrders)
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto max-w-3xl px-6 py-10">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Meus pedidos</h1>
          <p className="text-sm text-muted-foreground">
            Olá, {user?.full_name || user?.email}
          </p>
        </div>
        <div className="flex gap-2">
          <Link href="/create">
            <Button>Criar novo pedido</Button>
          </Link>
          <Button variant="outline" onClick={logout}>
            Sair
          </Button>
        </div>
      </div>

      {loading ? (
        <p className="text-muted-foreground">Carregando pedidos...</p>
      ) : orders.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            Você ainda não tem pedidos.{" "}
            <Link href="/create" className="underline">
              Criar o primeiro
            </Link>
          </CardContent>
        </Card>
      ) : (
        <ul className="space-y-3">
          {orders.map((order) => (
            <li key={order.id}>
              <Link href={`/dashboard/orders/${order.id}`}>
                <Card className="transition-colors hover:bg-accent">
                  <CardContent className="flex items-center justify-between py-4">
                    <div>
                      <p className="font-medium">{order.title}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(order.created_at).toLocaleString("pt-BR")}
                      </p>
                    </div>
                    <StatusBadge status={order.status} />
                  </CardContent>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
