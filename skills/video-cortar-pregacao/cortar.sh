#!/usr/bin/env bash
# Uso: cortar.sh <fonte> <INI HH:MM:SS> <FIM HH:MM:SS> <saida.mp4>
# Corte preciso (reencode) com fades de 0,5 s; tempos de fade absolutos na fonte,
# pois com -ss/-to após -i o ffmpeg filtra antes de cortar.
set -euo pipefail
export LC_ALL=C

[ $# -eq 4 ] || { echo "uso: $0 <fonte> <INI> <FIM> <saida.mp4>" >&2; exit 1; }
src=$1; ini=$2; fim=$3; out=$4

to_sec() { awk -F: '{ s=0; for (i=1; i<=NF; i++) s = s*60 + $i; printf "%.3f", s }' <<<"$1"; }

start=$(ffprobe -v error -show_entries format=start_time -of default=nw=1:nk=1 "$src")
start=${start:-0}; [ "$start" = "N/A" ] && start=0
i=$(to_sec "$ini"); f=$(to_sec "$fim")
fin=$(awk -v a="$i" -v s="$start" 'BEGIN { printf "%.3f", a + s }')
fout=$(awk -v b="$f" -v s="$start" 'BEGIN { printf "%.3f", b + s - 0.5 }')
dur=$(awk -v a="$i" -v b="$f" 'BEGIN { printf "%.3f", b - a }')
awk -v d="$dur" 'BEGIN { exit !(d > 1) }' || { echo "trecho inválido: $ini -> $fim" >&2; exit 1; }

mkdir -p "$(dirname "$out")"
ffmpeg -hide_banner -loglevel error -n -i "$src" -ss "$ini" -to "$fim" \
  -vf "fade=t=in:st=$fin:d=0.5,fade=t=out:st=$fout:d=0.5" \
  -af "afade=t=in:st=$fin:d=0.5,afade=t=out:st=$fout:d=0.5" \
  -c:v libx264 -crf 18 -preset medium -c:a aac -b:a 192k -movflags +faststart \
  "$out"

echo "esperado: ${dur}s"
ffprobe -v error -show_entries format=duration,size:stream=codec_type,codec_name,width,height -of compact "$out"
