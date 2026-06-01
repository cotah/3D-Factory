import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// Standard shadcn helper: merge conditional class names and dedupe Tailwind
// classes so later utilities win over earlier ones.
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
