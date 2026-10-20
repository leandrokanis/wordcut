#!/usr/bin/env python3
"""Corte vertical 9:16 (1080x1920) que acompanha o pregador, com legenda queimada.

Uso:
  vertical.py --fonte VIDEO --ini HH:MM:SS.mmm --fim HH:MM:SS.mmm --saida OUT.mp4 \
              [--srt LEGENDA.srt] [--srt-offset SEG] [--trabalho DIR]

O .srt deve ter tempos relativos ao corte (começando em 00:00:00).
--srt-offset soma segundos a todos os tempos da legenda (ex.: -0.3).
Requer: ffmpeg, opencv-python, numpy, scipy, Pillow (todos já instalados no Mac).
"""
import argparse, json, os, re, subprocess, sys
import cv2, numpy as np
from scipy.signal import savgol_filter, medfilt
from PIL import Image, ImageDraw, ImageFont

OW, OH = 1080, 1920
DZ, VMAX, AMAX, GAIN = 45.0, 6.0, 0.18, 0.10     # zona morta, vel/acel máx (px fonte/quadro)
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FS, Y_TOP, MAXW = 76, 1370, 1000                  # legenda: tamanho, topo (terço inferior), largura máx


def run(cmd):
    subprocess.run(cmd, check=True)


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height,r_frame_rate", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    s = json.loads(out)["streams"][0]
    num, den = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(num) / float(den)


def detect(clip, cache):
    """Por quadro: detecções de rosto (Haar frontal + perfil) ou corpo (HOG) e flag de corte de cena."""
    if os.path.exists(cache):
        return json.load(open(cache))
    face = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    prof = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_profileface.xml")
    hog = cv2.HOGDescriptor(); hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    cap, out, prev = cv2.VideoCapture(clip), [], None
    while True:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        h = cv2.calcHist([cv2.cvtColor(f, cv2.COLOR_BGR2HSV)], [0, 1], None, [32, 32], [0, 180, 0, 256])
        cv2.normalize(h, h)
        cut = prev is not None and cv2.compareHist(prev, h, cv2.HISTCMP_BHATTACHARYYA) > 0.35
        prev = h
        dets = []  # [x_centro, tamanho, tipo, y_cabeça]
        for c in (face, prof):
            for x, y, w, hh in c.detectMultiScale(g, 1.1, 5, minSize=(20, 20)):
                dets.append([x + w / 2, int(w), "face", y + hh / 2])
        for x, y, w, hh in prof.detectMultiScale(cv2.flip(g, 1), 1.1, 5, minSize=(20, 20)):
            dets.append([g.shape[1] - (x + w / 2), int(w), "face", y + hh / 2])
        if not dets:
            sc = 640 / f.shape[1]
            rects, _ = hog.detectMultiScale(cv2.resize(f, None, fx=sc, fy=sc), winStride=(8, 8))
            dets = [[(x + w / 2) / sc, int(hh / sc), "body", (y + hh * 0.15) / sc] for x, y, w, hh in rects]
        out.append({"cut": bool(cut), "dets": [[float(a), int(b), k, float(d)] for a, b, k, d in dets]})
    json.dump(out, open(cache, "w"))
    return out


def camera_path(dets, sw, sh, alvo=None):
    """Trajetória da janela: mesma pessoa por continuidade, suavização forte, zona morta, vel. limitada.
    alvo: posição horizontal (0–1) de quem seguir; sem alvo, segue o maior rosto."""
    cw = sh * 9 / 16
    raw, cur, miss, cuts = [], None, 0, []
    for i, o in enumerate(dets):
        c = [x for x in o["dets"] if x[3] < sh * 0.42]      # cabeças na parte de cima (ignora plateia)
        if o["cut"]:
            cur, miss = None, 0; cuts.append(i)
        if cur is None and c:
            if alvo is None:
                cur = max(c, key=lambda x: x[1])[0]           # maior rosto/corpo = pregador
            else:
                cur = min(c, key=lambda x: abs(x[0] - alvo * sw))[0]  # mais perto do alvo
        elif c:
            best = min(c, key=lambda x: abs(x[0] - cur))
            if abs(best[0] - cur) < 120 + 20 * miss:
                cur, miss = best[0], 0
            else:
                miss += 1
        else:
            miss += 1                                         # mantém última posição válida
        raw.append(cur)
    first = next((x for x in raw if x is not None), sw / 2)
    raw = np.array([first if x is None else x for x in raw], float)

    cam = np.empty_like(raw)
    bounds = [0] + cuts + [len(raw)]
    for a, b in zip(bounds[:-1], bounds[1:]):                 # cada cena separada: reposiciona sem deslizar
        if b <= a:
            continue
        seg = raw[a:b]
        if len(seg) >= 15:
            seg = medfilt(seg, 15)
        if len(seg) >= 91:
            seg = savgol_filter(seg, 91, 2)
        c, v = seg[0], 0.0
        for i, t in enumerate(seg):
            err = t - c
            want = 0.0 if abs(err) <= DZ else np.sign(err) * min(VMAX, (abs(err) - DZ) * GAIN)
            v += np.clip(want - v, -AMAX, AMAX); c += v; cam[a + i] = c
        if b - a >= 31:
            cam[a:b] = savgol_filter(cam[a:b], 31, 2)
    cam = np.clip(cam, cw / 2, sw - cw / 2)
    print(f"cortes de cena: {[round(i, 1) for i in cuts]} | "
          f"distância pregador-centro média {np.abs(raw - cam).mean():.0f}px, máx {np.abs(raw - cam).max():.0f}px "
          f"(meia janela {cw / 2:.0f}px)")
    return cam


def load_subs(path, offset):
    if not path:
        return []
    def sec(t):
        h, m, s = t.strip().replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    def layout(text):
        """Até 2 linhas: mantém as quebras do .srt se couberem, senão quebra equilibrada; reduz a fonte se preciso."""
        for size in range(FS, 47, -4):
            font = ImageFont.truetype(FONT, size)
            L = [x for x in text.split("\n") if x.strip()]
            if len(L) > 2 or any(font.getlength(x) > MAXW for x in L):
                w = text.split()
                k = min(range(1, len(w)) or [1], key=lambda i: max(font.getlength(" ".join(w[:i])), font.getlength(" ".join(w[i:]))))
                L = [x for x in (" ".join(w[:k]), " ".join(w[k:])) if x]
            if all(font.getlength(x) <= MAXW for x in L):
                return font, L
        sys.exit(f"legenda longa demais para 2 linhas: {text!r}")

    subs = []
    txt = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n").replace("\r", "\n").strip()
    for b in re.split(r"\n\s*\n", txt):
        p = b.split("\n")
        ti = next(i for i, x in enumerate(p) if "-->" in x)
        text = "\n".join(p[ti + 1:]).strip()
        if not text:
            continue
        a, z = (sec(x) + offset for x in p[ti].split("-->"))
        font, lines = layout(text)
        img = Image.new("RGBA", (OW, 220), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
        for i, ln in enumerate(lines):
            d.text((OW / 2, 12 + i * round(font.size * 1.21)), ln, font=font, anchor="ma", fill="white", stroke_width=6, stroke_fill="black")
        rgba = np.asarray(img).astype(np.float32)
        subs.append((a, z, rgba[..., 2::-1], rgba[..., 3:4] / 255))
    return subs


def render(clip, cam, subs, sw, sh, fps, out):
    k, cw = OH / sh, sh * 9 / 16
    n = len(cam)
    enc = subprocess.Popen(["ffmpeg", "-hide_banner", "-loglevel", "error", "-n",
        "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{OW}x{OH}", "-r", f"{fps}", "-i", "-",
        "-i", clip, "-map", "0:v", "-map", "1:a", "-vf", "format=yuv420p",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-t", f"{n / fps:.3f}", out], stdin=subprocess.PIPE)
    cap = cv2.VideoCapture(clip)
    for i in range(n):
        ok, f = cap.read()
        if not ok:
            break
        M = np.float32([[k, 0, -(cam[i] - cw / 2) * k], [0, k, 0]])  # recorte subpixel + escala
        img = cv2.warpAffine(f, M, (OW, OH), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
        t = i / fps
        for a, z, rgb, al in subs:
            if a <= t < z:
                r = img[Y_TOP:Y_TOP + rgb.shape[0]].astype(np.float32)
                img[Y_TOP:Y_TOP + rgb.shape[0]] = (rgb * al + r * (1 - al)).astype(np.uint8)
        enc.stdin.write(img.tobytes())
    enc.stdin.close()
    if enc.wait() != 0:
        sys.exit("ffmpeg falhou")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonte", required=True); ap.add_argument("--ini", required=True)
    ap.add_argument("--fim", required=True); ap.add_argument("--saida", required=True)
    ap.add_argument("--srt"); ap.add_argument("--srt-offset", type=float, default=0.0)
    ap.add_argument("--trabalho", default=None)
    ap.add_argument("--alvo", type=float, default=None,
                    help="posição horizontal (0–1) de quem seguir quando há mais de uma pessoa")
    a = ap.parse_args()
    base, ext = os.path.splitext(a.saida)
    v = 2
    while os.path.exists(a.saida):                          # nunca sobrescreve: usa -v2, -v3…
        a.saida = f"{base}-v{v}{ext}"; v += 1
    wd = a.trabalho or os.path.join(os.environ.get("TMPDIR", "/tmp"), "video-corte-vertical")
    os.makedirs(wd, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
    clip = os.path.join(wd, "trecho.mov")

    print("1/4 recortando trecho…")
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", a.fonte, "-ss", a.ini, "-to", a.fim,
         "-c:v", "libx264", "-crf", "12", "-preset", "fast", "-c:a", "pcm_s16le", clip])
    sw, sh, fps = probe(clip)
    print(f"   origem {sw}x{sh} @ {fps:g} fps")
    print("2/4 detectando pregador (pode levar minutos)…")
    dets = detect(clip, os.path.join(wd, "dets.json"))
    hit = sum(bool(o["dets"]) for o in dets)
    print(f"   {hit}/{len(dets)} quadros com detecção")
    print("3/4 calculando trajetória…")
    cam = camera_path(dets, sw, sh, a.alvo)
    json.dump(cam.tolist(), open(os.path.join(wd, "cam.json"), "w"))
    print("4/4 renderizando…")
    render(clip, cam, load_subs(a.srt, a.srt_offset), sw, sh, fps, a.saida)
    print("pronto:", a.saida)


if __name__ == "__main__":
    main()
