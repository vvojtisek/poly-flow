// Loudness envelope of a short clip, for drawing a rhythm outline. Signal shape only: it says
// nothing about pronunciation quality.

export interface Envelope {
  bins: number[]; // 0..1, speech only (leading and trailing silence trimmed)
  seconds: number; // duration of the trimmed speech
}

const SILENCE = 0.08; // fraction of the peak RMS treated as silence at the edges

export function envelopeOf(samples: Float32Array, sampleRate: number, bins = 96): Envelope {
  const frame = Math.max(1, Math.round(sampleRate * 0.01)); // 10 ms frames
  const rms: number[] = [];
  for (let i = 0; i < samples.length; i += frame) {
    let sum = 0;
    const end = Math.min(samples.length, i + frame);
    for (let j = i; j < end; j++) sum += samples[j]! * samples[j]!;
    rms.push(Math.sqrt(sum / (end - i)));
  }
  const peak = Math.max(...rms, 1e-9);
  let first = rms.findIndex((v) => v >= peak * SILENCE);
  let last = rms.length - 1 - [...rms].reverse().findIndex((v) => v >= peak * SILENCE);
  if (first < 0) {
    first = 0;
    last = rms.length - 1;
  }
  const speech = rms.slice(first, last + 1);
  const out: number[] = [];
  for (let b = 0; b < bins; b++) {
    const from = Math.floor((b * speech.length) / bins);
    const to = Math.max(from + 1, Math.floor(((b + 1) * speech.length) / bins));
    let m = 0;
    for (let i = from; i < to && i < speech.length; i++) m = Math.max(m, speech[i]!);
    out.push(m / peak);
  }
  return { bins: out, seconds: (speech.length * frame) / sampleRate };
}

let ctx: AudioContext | null = null;

/** Decode an audio blob or object URL and compute its envelope; null if it cannot be decoded. */
export async function envelopeFromUrl(url: string): Promise<Envelope | null> {
  try {
    const buf = await (await fetch(url)).arrayBuffer();
    ctx ??= new AudioContext();
    const audio = await ctx.decodeAudioData(buf);
    return envelopeOf(audio.getChannelData(0), audio.sampleRate);
  } catch {
    return null;
  }
}
