/** SSE hook that listens to /api/events and invalidates TanStack Query caches. */

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { SSEvent } from "@/api/types";

/** Minimum ms between cache invalidation rounds. */
const INVALIDATION_DEBOUNCE_MS = 5_000;

export function useEventSource() {
  const queryClient = useQueryClient();
  const lastInvalidation = useRef(0);
  const pendingTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const es = new EventSource("/api/events");

    const invalidateAll = () => {
      lastInvalidation.current = Date.now();
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["sessions"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
    };

    const scheduleInvalidation = () => {
      const elapsed = Date.now() - lastInvalidation.current;
      if (elapsed >= INVALIDATION_DEBOUNCE_MS) {
        invalidateAll();
      } else if (!pendingTimer.current) {
        pendingTimer.current = setTimeout(() => {
          pendingTimer.current = null;
          invalidateAll();
        }, INVALIDATION_DEBOUNCE_MS - elapsed);
      }
      // If a timer is already pending, skip — it will handle it.
    };

    es.onmessage = (e) => {
      try {
        const event: SSEvent = JSON.parse(e.data);
        if (
          event.type === "session_imported" ||
          event.type === "import_complete"
        ) {
          scheduleInvalidation();
        }
      } catch {
        // ignore malformed events
      }
    };

    es.onerror = () => {
      // EventSource auto-reconnects; nothing to do here
    };

    return () => {
      es.close();
      if (pendingTimer.current) {
        clearTimeout(pendingTimer.current);
      }
    };
  }, [queryClient]);
}
