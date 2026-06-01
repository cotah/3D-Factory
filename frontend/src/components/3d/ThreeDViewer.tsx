"use client";

import { Component, type ReactNode, Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import {
  Bounds,
  Center,
  ContactShadows,
  Html,
  OrbitControls,
  useGLTF,
} from "@react-three/drei";

interface Props {
  modelUrl: string;
  format?: "glb" | "obj" | "stl";
  height?: number;
}

function Model({ url }: { url: string }) {
  // GLB only for now; OBJ/STL are a TODO.
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

function Loader() {
  return (
    <Html center>
      <div className="flex flex-col items-center gap-2 text-white">
        <span className="h-6 w-6 animate-spin rounded-full border-2 border-white/30 border-t-white" />
        <span className="text-sm">Carregando modelo...</span>
      </div>
    </Html>
  );
}

// Catches GLTF load failures so a broken URL shows a friendly message instead
// of crashing the whole page.
class ViewerErrorBoundary extends Component<
  { children: ReactNode; fallback: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };
  static getDerivedStateFromError() {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) return this.props.fallback;
    return this.props.children;
  }
}

export function ThreeDViewer({ modelUrl, height = 400 }: Props) {
  return (
    <div
      style={{ height, background: "#1a1a1a", borderRadius: 8, overflow: "hidden" }}
    >
      <ViewerErrorBoundary
        fallback={
          <div className="flex h-full items-center justify-center px-4 text-center text-sm text-white/80">
            Não foi possível carregar o modelo 3D.
          </div>
        }
      >
        <Canvas camera={{ position: [0, 0, 5], fov: 45 }} dpr={[1, 2]}>
          {/* Explicit lights instead of Environment(preset) to avoid a runtime
              HDR fetch from a CDN — keeps the viewer reliable offline. */}
          <ambientLight intensity={0.6} />
          <directionalLight position={[5, 5, 5]} intensity={1.1} />
          <directionalLight position={[-5, -2, -5]} intensity={0.4} />
          <Suspense fallback={<Loader />}>
            <Bounds fit clip observe margin={1.2}>
              <Center>
                <Model url={modelUrl} />
              </Center>
            </Bounds>
            <ContactShadows
              position={[0, -1.2, 0]}
              opacity={0.35}
              blur={2.5}
              far={4}
            />
          </Suspense>
          <OrbitControls enablePan enableZoom enableRotate makeDefault />
        </Canvas>
      </ViewerErrorBoundary>
    </div>
  );
}
