"use client";

// Records one short spoken answer with MediaRecorder. The microphone is released as soon as a
// recording ends or is cancelled. Needs a secure context (HTTPS or localhost).

import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderState =
  | { kind: "idle" }
  | { kind: "recording" }
  | { kind: "error"; reason: "unsupported" | "denied" | "failed" };

const MAX_MS = 6000; // one word or a short phrase

function supported(): boolean {
  return (
    typeof window !== "undefined" &&
    window.isSecureContext &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== "undefined"
  );
}

export function useRecorder(onRecording: (recording: Blob) => void) {
  const [state, setState] = useState<RecorderState>({ kind: "idle" });
  const recorder = useRef<MediaRecorder | null>(null);
  const cancelled = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const deliver = useRef(onRecording);
  deliver.current = onRecording;

  const release = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    recorder.current?.stream.getTracks().forEach((t) => t.stop());
    recorder.current = null;
  }, []);

  const start = useCallback(async () => {
    if (!supported()) {
      setState({ kind: "error", reason: "unsupported" });
      return;
    }
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    } catch (e) {
      const denied = e instanceof DOMException && (e.name === "NotAllowedError" || e.name === "SecurityError");
      setState({ kind: "error", reason: denied ? "denied" : "unsupported" });
      return;
    }
    const chunks: Blob[] = [];
    const rec = new MediaRecorder(stream);
    recorder.current = rec;
    cancelled.current = false;
    rec.ondataavailable = (e) => {
      if (e.data.size) chunks.push(e.data);
    };
    rec.onerror = () => {
      release();
      setState({ kind: "error", reason: "failed" });
    };
    rec.onstop = () => {
      release();
      setState({ kind: "idle" });
      if (!cancelled.current && chunks.length) deliver.current(new Blob(chunks, { type: rec.mimeType || "audio/webm" }));
    };
    rec.start();
    setState({ kind: "recording" });
    timer.current = setTimeout(() => rec.state === "recording" && rec.stop(), MAX_MS);
  }, [release]);

  const stop = useCallback(() => {
    if (recorder.current?.state === "recording") recorder.current.stop();
  }, []);

  const cancel = useCallback(() => {
    cancelled.current = true;
    stop();
  }, [stop]);

  const reset = useCallback(() => setState({ kind: "idle" }), []);

  // Leaving the task (or the page) never keeps the microphone open.
  useEffect(
    () => () => {
      cancelled.current = true;
      if (recorder.current?.state === "recording") recorder.current.stop();
      release();
    },
    [release],
  );

  return { state, start, stop, cancel, reset };
}
