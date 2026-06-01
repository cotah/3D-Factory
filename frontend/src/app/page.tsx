import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 px-6 text-center">
      <div className="space-y-3">
        <h1 className="text-5xl font-bold tracking-tight">Print3D</h1>
        <p className="text-lg text-muted-foreground">
          Peças 3D personalizadas com IA
        </p>
        <p className="mx-auto max-w-md text-sm text-muted-foreground">
          Descreva o que você quer, aprove o conceito gerado por IA e receba seu
          modelo 3D pronto para impressão — com apoio de um designer humano
          quando necessário.
        </p>
      </div>

      <div className="flex gap-4">
        <Link href="/create">
          <Button size="lg">Criar pedido</Button>
        </Link>
        <Link href="/login">
          <Button size="lg" variant="outline">
            Entrar
          </Button>
        </Link>
      </div>
    </main>
  );
}
