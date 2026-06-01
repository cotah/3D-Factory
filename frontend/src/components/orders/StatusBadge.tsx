import { ORDER_STATUS_COLORS, ORDER_STATUS_LABELS, type OrderStatus } from "@/types";
import { cn } from "@/lib/utils";

export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        ORDER_STATUS_COLORS[status],
      )}
    >
      {ORDER_STATUS_LABELS[status]}
    </span>
  );
}
