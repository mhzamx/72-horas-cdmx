"""v0.2 — Gráficas 10-12. Paleta validada para daltonismo (azul/naranja),
etiquetas directas en cada marca: la identidad nunca depende solo del color."""
from __future__ import annotations
import pandas as pd
import matplotlib.pyplot as plt

from .config import OUTPUT_TABLES, OUTPUT_CHARTS

BLUE, BLUE_BAND, ORANGE, GREY, INK, INK2 = "#2a78d6", "#b7d3f6", "#eb6834", "#9AA5B1", "#0b0b0b", "#52514e"
plt.rcParams.update({"figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
                     "axes.edgecolor": INK2, "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2})
NOTE = "Fuente: CBPCDMX, Registro Interno (reportes 25-jun-2019 a 14-nov-2022; corte 15-nov-2022). Solo fechas, sin hora: 72 h = ≤3 días calendario."


def _scenarios() -> None:
    df = pd.read_csv(OUTPUT_TABLES / "km_scenarios_v02.csv")
    d = df[df["horizonte"] == 3].set_index("escenario").loc[["E0", "E1", "E2-baja", "E3", "E2-alta"]]
    labels = ["E0\nversión publicada\n(corte corregido)", "E1\n+ localizados antes\ndel registro", "E2-baja\nsin fecha = no\nlocalizados",
              "E3 (principal)\nsin fecha\nimputados", "E2-alta\nsin fecha =\ndía 0"]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    colors = [GREY, GREY, GREY, BLUE, GREY]
    x = range(len(d))
    ax.bar(x, d["pct"], color=colors, width=0.6, edgecolor="#fcfcfb", linewidth=2)
    ax.errorbar(x, d["pct"], yerr=[d["pct"] - d["ic_baja"], d["ic_alta"] - d["pct"]],
                fmt="none", ecolor=INK2, elinewidth=1, capsize=4)
    for i, (p, hi) in enumerate(zip(d["pct"], d["ic_alta"])):
        ax.text(i, hi + 1, f"{p:.1f}%", ha="center", va="bottom", fontsize=11, color=INK,
                fontweight="bold" if d.index[i] == "E3" else "normal")
    ax.set_xticks(list(x), labels, fontsize=9)
    ax.set_ylim(0, max(d["ic_alta"]) + 8)
    ax.set_ylabel("% con localización documentada en ≤3 días")
    ax.set_title("La cifra a 72 horas cambia según cómo se tratan los datos\n(barras: IC 95% bootstrap)", loc="left")
    fig.text(0.01, 0.01, NOTE, fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUTPUT_CHARTS / "10_scenarios_v02.png", dpi=180)
    plt.close(fig)


def _curve_e3() -> None:
    c = pd.read_csv(OUTPUT_TABLES / "km_curve_e3_v02.csv")
    c = c[c["t"] <= 30]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.fill_between(c["t"], c["ic_baja"], c["ic_alta"], step="post", color=BLUE_BAND, linewidth=0,
                    label="IC 95% bootstrap")
    ax.step(c["t"], c["pct_localizado"], where="post", color=BLUE, linewidth=2, label="E3 (principal)")
    for day in (1, 3, 7, 30):
        row = c[c["t"] == day].iloc[0]
        ax.plot(day, row["pct_localizado"], "o", color=BLUE, markersize=8, markeredgecolor="#fcfcfb", markeredgewidth=2)
        ax.annotate(f"{row['pct_localizado']:.1f}% a {day} d", (day, row["pct_localizado"]),
                    textcoords="offset points", xytext=(6, -14), fontsize=9, color=INK)
    ax.axvline(3, color=INK2, linestyle=":", linewidth=1)
    ax.set_xlim(0, 30); ax.set_ylim(0, 70)
    ax.set_xlabel("Días desde el reporte"); ax.set_ylabel("% acumulado con localización documentada")
    ax.set_title("Localización documentada acumulada desde el reporte (estimación principal E3)", loc="left")
    ax.legend(loc="lower right", frameon=False)
    fig.text(0.01, 0.01, NOTE, fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUTPUT_CHARTS / "11_km_e3_v02.png", dpi=180)
    plt.close(fig)


def _cif_exact() -> None:
    c = pd.read_csv(OUTPUT_TABLES / "cif_exact_v02.csv")
    c = c[(c["poblacion"] == "E3") & (c["t"] <= 30)]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    ax.fill_between(c["t"], 0, c["con_vida"], step="post", color=BLUE, linewidth=0, label="Con vida")
    ax.fill_between(c["t"], c["con_vida"], c["con_vida"] + c["sin_vida"], step="post", color=ORANGE,
                    linewidth=0, label="Sin vida")
    ax.step(c["t"], c["con_vida"], where="post", color="#fcfcfb", linewidth=2)
    last = c.iloc[-1]
    ax.text(30.3, last["con_vida"] / 2, f"Con vida\n{last['con_vida']:.1f}%", fontsize=9, color=INK, va="center")
    ax.text(30.3, last["con_vida"] + last["sin_vida"] / 2 + 2, f"Sin vida\n{last['sin_vida']:.1f}%", fontsize=9,
            color=INK, va="center")
    ax.set_xlim(0, 30); ax.set_ylim(0, 70)
    ax.set_xlabel("Días desde el reporte (fecha de cierre administrativo, NO fecha de fallecimiento)")
    ax.set_ylabel("% acumulado (Aalen-Johansen exacto)")
    ax.set_title("Desenlace registrado al localizar: incidencia acumulada por tipo (E3)", loc="left")
    ax.legend(loc="upper left", frameon=False)
    fig.text(0.01, 0.01, NOTE, fontsize=7, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 0.93, 1))
    fig.savefig(OUTPUT_CHARTS / "12_cif_exact_v02.png", dpi=180)
    plt.close(fig)


def make_charts_v02() -> None:
    _scenarios(); _curve_e3(); _cif_exact()
