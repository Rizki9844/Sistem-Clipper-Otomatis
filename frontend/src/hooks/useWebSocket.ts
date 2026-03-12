"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { WSProgressEvent } from "@/lib/api/types";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000/api/v1/ws";

interface UseWebSocketOptions {
    jobId: string;
    onProgress?: (event: WSProgressEvent) => void;
    enabled?: boolean;
}

export function useWebSocket({ jobId, onProgress, enabled = true }: UseWebSocketOptions) {
    const wsRef = useRef<WebSocket | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [lastEvent, setLastEvent] = useState<WSProgressEvent | null>(null);
    const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
    const pingTimer = useRef<NodeJS.Timeout | null>(null);

    const connect = useCallback(() => {
        if (!enabled || !jobId) return;

        const ws = new WebSocket(`${WS_URL}/ws/progress?job_id=${jobId}`);
        wsRef.current = ws;

        ws.onopen = () => {
            setIsConnected(true);
            // Send ping every 25 seconds to keep alive
            pingTimer.current = setInterval(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.send("ping");
                }
            }, 25000);
        };

        ws.onmessage = (event) => {
            try {
                const data: WSProgressEvent = JSON.parse(event.data);
                if (data.type === "heartbeat" || data.type === "pong") return;
                setLastEvent(data);
                onProgress?.(data);
            } catch {
                // ignore parse errors
            }
        };

        ws.onclose = () => {
            setIsConnected(false);
            if (pingTimer.current) clearInterval(pingTimer.current);
            // Auto-reconnect after 3 seconds
            reconnectTimer.current = setTimeout(connect, 3000);
        };

        ws.onerror = () => {
            ws.close();
        };
    }, [jobId, onProgress, enabled]);

    useEffect(() => {
        connect();
        return () => {
            if (wsRef.current) wsRef.current.close();
            if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
            if (pingTimer.current) clearInterval(pingTimer.current);
        };
    }, [connect]);

    const disconnect = useCallback(() => {
        if (wsRef.current) wsRef.current.close();
        if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    }, []);

    return { isConnected, lastEvent, disconnect };
}
