import { useEffect, useRef, useCallback } from "react";

const WS_BASE = import.meta.env.VITE_WS_BASE
  || (import.meta.env.VITE_API_BASE || "/api").replace(/^http/, "ws").replace(/\/api$/, "");

export function useWebSocket(sessionId, onMessage) {
  const socketRef = useRef(null);
  const handlerRef = useRef(onMessage);
  handlerRef.current = onMessage;

  const connect = useCallback(() => {
    if (!sessionId || import.meta.env.VITE_USE_MOCK === "true") return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const base = WS_BASE && WS_BASE.startsWith("ws") ? WS_BASE : `${protocol}//${host}`;
    const url = `${base.replace(/\/$/, "")}/ws?session_id=${encodeURIComponent(sessionId)}`;

    const socket = new WebSocket(url);
    socketRef.current = socket;

    socket.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handlerRef.current?.(payload);
      } catch {
        // ignore malformed frames
      }
    };

    socket.onclose = () => {
      socketRef.current = null;
    };
  }, [sessionId]);

  useEffect(() => {
    connect();
    return () => socketRef.current?.close();
  }, [connect]);

  return socketRef;
}
