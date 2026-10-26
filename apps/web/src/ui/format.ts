/** ``2026-10-18`` as ``18/10/2026``, without going through a time zone. */
export function formatDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-");
  return `${day}/${month}/${year}`;
}

/** Seconds as ``h:mm:ss``, or ``m:ss`` under an hour, as the prototype shows them. */
export function formatDuration(seconds: number): string {
  const whole = Math.max(0, Math.floor(seconds));
  const hours = Math.floor(whole / 3600);
  const minutes = Math.floor((whole % 3600) / 60);
  const rest = String(whole % 60).padStart(2, "0");
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${rest}` : `${minutes}:${rest}`;
}

/** An ISO moment as ``21/10/2026 19:05``, in the wall time it was written with. */
export function formatDateTime(isoMoment: string): string {
  return `${formatDate(isoMoment.slice(0, 10))} ${isoMoment.slice(11, 16)}`;
}
