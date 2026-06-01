import {
  ORDER_LIFECYCLE,
  ORDER_STATUS_LABELS,
  type OrderStatus,
} from "@/types";
import { cn } from "@/lib/utils";

// Renders the happy-path lifecycle with the current step highlighted. Branch
// states (cancelled, designer_required, ai_revision_required) are shown as a
// standalone note since they fall outside the linear path.
const BRANCH_STATES: OrderStatus[] = [
  "cancelled",
  "designer_required",
  "ai_revision_required",
];

export function OrderStatusTimeline({ status }: { status: OrderStatus }) {
  const currentIndex = ORDER_LIFECYCLE.indexOf(status);
  const isBranch = BRANCH_STATES.includes(status);

  return (
    <div>
      <ol className="space-y-2">
        {ORDER_LIFECYCLE.map((step, index) => {
          const done = currentIndex >= 0 && index < currentIndex;
          const active = index === currentIndex;
          return (
            <li key={step} className="flex items-center gap-3">
              <span
                className={cn(
                  "flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs",
                  done && "border-green-500 bg-green-500 text-white",
                  active && "border-primary bg-primary text-primary-foreground",
                  !done && !active && "border-slate-300 text-slate-400",
                )}
              >
                {done ? "✓" : index + 1}
              </span>
              <span
                className={cn(
                  "text-sm",
                  active ? "font-semibold text-foreground" : "text-muted-foreground",
                )}
              >
                {ORDER_STATUS_LABELS[step]}
              </span>
            </li>
          );
        })}
      </ol>

      {isBranch && (
        <p className="mt-4 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Estado atual: <strong>{ORDER_STATUS_LABELS[status]}</strong>
        </p>
      )}
    </div>
  );
}
