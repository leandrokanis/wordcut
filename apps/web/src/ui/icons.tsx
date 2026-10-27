// Stroke icons of docs/prototype/wordcut.html.

function Icon({ path }: { path: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d={path} />
    </svg>
  );
}

export function CloseIcon() {
  return <Icon path="M18 6 6 18M6 6l12 12" />;
}

export function PlusIcon() {
  return <Icon path="M12 5v14M5 12h14" />;
}

export function GearIcon() {
  return (
    <Icon path="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
  );
}

export function BackIcon() {
  return <Icon path="M19 12H5M12 19l-7-7 7-7" />;
}

export function FilmIcon() {
  return <Icon path="M5 5h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM7 5v14M17 5v14M3 9.5h4M3 14.5h4M17 9.5h4M17 14.5h4" />;
}

export function WaveIcon() {
  return <Icon path="M3 12h1M7 8v8M11 5v14M15 9v6M19 7v10M22 12h-1" />;
}

export function PlayIcon() {
  return (
    <svg viewBox="0 0 12 12" aria-hidden="true">
      <path d="M2 1l9 5-9 5z" fill="currentColor" />
    </svg>
  );
}

export function PauseIcon() {
  return (
    <svg viewBox="0 0 12 12" aria-hidden="true">
      <path d="M2 1h3v10H2zM7 1h3v10H7z" fill="currentColor" />
    </svg>
  );
}

export function DotsIcon() {
  return (
    <Icon path="M5 10.7a1.3 1.3 0 1 0 0 2.6 1.3 1.3 0 0 0 0-2.6zM12 10.7a1.3 1.3 0 1 0 0 2.6 1.3 1.3 0 0 0 0-2.6zM19 10.7a1.3 1.3 0 1 0 0 2.6 1.3 1.3 0 0 0 0-2.6z" />
  );
}

export function CaptionIcon() {
  return <Icon path="M5 5h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2zM10 10.5a2 2 0 1 0 0 3M17 10.5a2 2 0 1 0 0 3" />;
}

export function UndoIcon() {
  return <Icon path="M9 14 4 9l5-5M4 9h10.5a5.5 5.5 0 0 1 0 11H11" />;
}

export function RedoIcon() {
  return <Icon path="m15 14 5-5-5-5M20 9H9.5a5.5 5.5 0 0 0 0 11H13" />;
}

export function ScissorsIcon() {
  return (
    <Icon path="M3 6a3 3 0 1 0 6 0 3 3 0 1 0-6 0zM3 18a3 3 0 1 0 6 0 3 3 0 1 0-6 0zM20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12" />
  );
}

export function LeftIcon() {
  return <Icon path="m15 18-6-6 6-6" />;
}

export function RightIcon() {
  return <Icon path="m9 18 6-6-6-6" />;
}

export function TrashIcon() {
  return <Icon path="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14" />;
}
