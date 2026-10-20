"""Converte legenda automática do YouTube (.vtt com tempos por palavra) em
transcrição legível com tempos.

Saída: uma linha por bloco de legenda, no formato
    [HH:MM:SS.mmm] texto
seguida, com --palavras, de cada palavra com seu tempo de início.

Uso: python3 -I transcricao.py legenda.vtt saida.txt [--palavras]
"""
import re
import sys

TS = r"(\d{2}:\d{2}:\d{2}\.\d{3})"


def seg(t):
    h, m, s = t.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def fmt(x):
    h, r = divmod(x, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def palavras(caminho):
    """Lista (tempo, palavra) a partir das linhas com marcação <c>."""
    out = []
    ini = None
    for linha in open(caminho, encoding="utf-8"):
        linha = linha.rstrip("\n")
        m = re.match(TS + r" -->", linha)
        if m:
            ini = seg(m.group(1))
            continue
        if "<c>" not in linha or ini is None:
            continue
        # primeira palavra começa no início do bloco; as demais têm <tempo>
        partes = re.split(r"<" + TS + r">", linha)
        primeira = re.sub(r"<[^>]+>", "", partes[0]).strip()
        if primeira:
            out.append((ini, primeira))
        for i in range(1, len(partes), 2):
            p = re.sub(r"<[^>]+>", "", partes[i + 1]).strip()
            if p:
                out.append((seg(partes[i]), p))
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    com_palavras = "--palavras" in sys.argv
    ps = palavras(src)
    if not ps:
        sys.exit("nenhuma palavra com tempo encontrada (legenda não é automática?)")
    linhas, atual, t0 = [], [], None
    for t, p in ps:
        if t0 is None:
            t0 = t
        atual.append(p)
        # quebra em fim de frase ou a cada ~15 palavras
        if p[-1] in ".?!" or len(atual) >= 15:
            linhas.append(f"[{fmt(t0)}] {' '.join(atual)}")
            atual, t0 = [], None
    if atual:
        linhas.append(f"[{fmt(t0)}] {' '.join(atual)}")
    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")
        if com_palavras:
            f.write("\n# palavras\n")
            f.write("\n".join(f"{fmt(t)} {p}" for t, p in ps) + "\n")
    print(f"{len(ps)} palavras, {len(linhas)} linhas -> {dst}")


if __name__ == "__main__":
    main()
