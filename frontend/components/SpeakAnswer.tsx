"use client";

import { Loader2, Mic, Square, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui";
import { useRecorder } from "@/hooks/useRecorder";
import { ApiError, newIdempotencyKey, submitSpeech, type AnswerResult } from "@/lib/api";
import { cs } from "@/lib/i18n/cs";

/** Answer a recall task by voice. Typing stays available whatever happens here. */
export function SpeakAnswer({
  taskId,
  disabled,
  onResult,
}: {
  taskId: string;
  disabled: boolean;
  onResult: (result: AnswerResult) => void;
}) {
  const [sending, setSending] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const recorder = useRecorder((recording) => void send(recording));

  async function send(recording: Blob) {
    setSending(true);
    setProblem(null);
    try {
      onResult(await submitSpeech(taskId, newIdempotencyKey(), recording));
    } catch (e) {
      setProblem(e instanceof ApiError && e.status === 503 ? cs.audio.sttUnavailable : cs.audio.failed);
    } finally {
      setSending(false);
    }
  }

  const err = recorder.state.kind === "error" ? recorder.state.reason : null;
  const message = problem ?? (err ? cs.audio[err] : null);

  return (
    <div className="flex flex-col items-center gap-2">
      {sending ? (
        <p role="status" className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="size-4 animate-spin" aria-hidden /> {cs.audio.listening}
        </p>
      ) : recorder.state.kind === "recording" ? (
        <div className="flex w-full gap-2">
          <Button className="flex-1 animate-pulse" onClick={recorder.stop} autoFocus>
            <Square className="size-4" aria-hidden /> {cs.audio.recording}
          </Button>
          <Button variant="ghost" onClick={recorder.cancel} aria-label={cs.audio.cancel}>
            <X className="size-4" aria-hidden />
          </Button>
        </div>
      ) : (
        <Button
          variant="secondary"
          className="w-full"
          disabled={disabled}
          onClick={() => {
            setProblem(null);
            recorder.reset();
            void recorder.start();
          }}
        >
          <Mic className="size-4" aria-hidden /> {cs.audio.speak}
        </Button>
      )}
      {message && (
        <p role="alert" className="text-center text-sm text-amber-700 dark:text-amber-300">
          {message}
        </p>
      )}
    </div>
  );
}
