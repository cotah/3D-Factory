"use client";

// Wrap any page that requires authentication. While the auth state is loading
// it shows a spinner; if there is no user it redirects to /login.

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/AuthProvider";

export function ProtectedRoute({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles?: string[];
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Carregando...
      </div>
    );
  }

  if (roles && !roles.includes(user.role)) {
    return (
      <div className="flex min-h-screen items-center justify-center text-muted-foreground">
        Você não tem acesso a esta área.
      </div>
    );
  }

  return <>{children}</>;
}
