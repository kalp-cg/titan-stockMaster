import { useEffect, useRef, useState } from "react";

export function useWebSocket(onMessage?: (msg: any) => void) {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let active = true;
    let reconnectTimeout: any;

    function connect() {
      const ws = new WebSocket("ws://localhost:8000/ws");
      wsRef.current = ws;

      ws.onopen = () => {
        if (active) {
          setConnected(true);
          console.log("WS Connected");
        }
      };

      ws.onmessage = (event) => {
        if (!active) return;
        try {
          const data = JSON.parse(event.data);
          if (onMessage) {
            onMessage(data);
          }
        } catch (e) {
          console.error("Failed to parse WS message:", e);
        }
      };

      ws.onclose = () => {
        if (active) {
          setConnected(false);
          console.log("WS Disconnected, reconnecting...");
          reconnectTimeout = setTimeout(connect, 3000);
        }
      };

      ws.onerror = (e) => {
        console.error("WS Error:", e);
      };
    }

    connect();

    return () => {
      active = false;
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [onMessage]);

  return connected;
}
