/** An analog clock face (12 hours) for telling-the-time practice. Purely presentational. */
export function ClockFace({ hour, minute, size = 160, label }: { hour: number; minute: number; size?: number; label: string }) {
  const hourAngle = ((hour % 12) + minute / 60) * 30;
  const minuteAngle = minute * 6;
  return (
    <svg viewBox="-50 -50 100 100" width={size} height={size} role="img" aria-label={label} className="shrink-0">
      <circle r="47" className="fill-white stroke-slate-300 dark:fill-slate-900 dark:stroke-slate-600" strokeWidth="2" />
      {Array.from({ length: 60 }, (_, i) => {
        const major = i % 5 === 0;
        return (
          <line
            key={i}
            y1={major ? -42 : -44}
            y2="-46"
            transform={`rotate(${i * 6})`}
            className={major ? "stroke-slate-700 dark:stroke-slate-200" : "stroke-slate-300 dark:stroke-slate-600"}
            strokeWidth={major ? 2 : 0.8}
            strokeLinecap="round"
          />
        );
      })}
      {Array.from({ length: 12 }, (_, i) => {
        const n = i + 1;
        const a = (n * 30 * Math.PI) / 180;
        return (
          <text
            key={n}
            x={Math.sin(a) * 34}
            y={-Math.cos(a) * 34}
            textAnchor="middle"
            dominantBaseline="central"
            fontSize="9"
            fontWeight="600"
            className="fill-slate-600 dark:fill-slate-300"
          >
            {n}
          </text>
        );
      })}
      <line y2="-22" transform={`rotate(${hourAngle})`} className="stroke-slate-900 dark:stroke-white" strokeWidth="4.5" strokeLinecap="round" />
      <line y2="-36" transform={`rotate(${minuteAngle})`} className="stroke-brand-500" strokeWidth="2.5" strokeLinecap="round" />
      <circle r="3" className="fill-brand-500" />
    </svg>
  );
}
