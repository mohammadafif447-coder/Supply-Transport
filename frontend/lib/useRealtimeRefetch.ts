"use client";

import { useEffect, useRef } from "react";
import { createClient } from "@/lib/supabase/client";

/**
 * Subscribes to Supabase Realtime `postgres_changes` on the given tables and
 * calls `onChange` whenever a row changes, and again whenever the channel
 * (re)reaches `SUBSCRIBED` — covering the reconnect-refetch requirement in
 * docs/02-SRS.md §2.2 (Next.js refetches REST state once the socket comes
 * back up, since realtime alone can't be trusted to have delivered every
 * event missed while disconnected).
 */
export function useRealtimeRefetch(channelName: string, tables: string[], onChange: () => void) {
  const onChangeRef = useRef(onChange);
  const tablesRef = useRef(tables);

  useEffect(() => {
    onChangeRef.current = onChange;
    tablesRef.current = tables;
  });

  useEffect(() => {
    const supabase = createClient();
    let channel = supabase.channel(channelName);
    for (const table of tablesRef.current) {
      channel = channel.on(
        "postgres_changes",
        { event: "*", schema: "public", table },
        () => onChangeRef.current()
      );
    }
    channel.subscribe((status) => {
      if (status === "SUBSCRIBED") onChangeRef.current();
    });

    return () => {
      supabase.removeChannel(channel);
    };
  }, [channelName]);
}
