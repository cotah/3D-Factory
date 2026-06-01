"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AxiosError } from "axios";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { ordersApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const schema = z.object({
  title: z.string().min(3, "Título precisa de ao menos 3 caracteres"),
  description: z.string().optional(),
  category: z.string().optional(),
  size: z.string().optional(),
  colors: z.string().optional(),
  material: z.string().optional(),
  deadline: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

function CreateOrderContent() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    setServerError(null);
    try {
      const order = await ordersApi.create(values);
      router.push(`/dashboard/orders/${order.id}`);
    } catch (err) {
      const detail =
        err instanceof AxiosError
          ? (err.response?.data?.detail as string) ?? "Falha ao criar pedido"
          : "Falha ao criar pedido";
      setServerError(detail);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-10">
      <Card>
        <CardHeader>
          <CardTitle>Criar pedido</CardTitle>
          <CardDescription>
            Descreva a peça que você quer imprimir.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="title">Título *</Label>
              <Input id="title" {...register("title")} />
              {errors.title && (
                <p className="text-sm text-destructive">{errors.title.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Descrição</Label>
              <Textarea id="description" rows={4} {...register("description")} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="category">Categoria</Label>
                <Input id="category" {...register("category")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="size">Tamanho</Label>
                <Input id="size" placeholder="ex: 10cm" {...register("size")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="colors">Cores</Label>
                <Input id="colors" {...register("colors")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="material">Material</Label>
                <Input id="material" placeholder="PLA, PETG..." {...register("material")} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="deadline">Prazo</Label>
                <Input id="deadline" {...register("deadline")} />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="notes">Notas</Label>
              <Textarea id="notes" rows={3} {...register("notes")} />
            </div>

            {serverError && (
              <p className="text-sm text-destructive">{serverError}</p>
            )}

            <div className="flex gap-2">
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Criando..." : "Criar pedido"}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push("/dashboard")}
              >
                Cancelar
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}

export default function CreateOrderPage() {
  return (
    <ProtectedRoute>
      <CreateOrderContent />
    </ProtectedRoute>
  );
}
