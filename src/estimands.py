"""v0.2 — Estimandos corregidos (doc «03 — METODOLOGÍA DE EJECUCIÓN v0.2»).

Correcciones respecto a la versión de 79 rutas (que se conserva intacta):
  (C1 corte fijo y C3 Aalen-Johansen exacto ya venían corregidos en la versión
  base `entrega_validacion_final_3`; aquí se reutiliza CUTOFF_DATE y se aplica
  el mismo estimador exacto a las nuevas poblaciones.)
  C2  Población completa por clases (VALIDO, AMBIGUO, SIN_FECHA, IMPOSIBLE,
      ABIERTO) y escenarios E0-E3; E3 = estimación principal con imputación
      múltiple de los localizados sin fecha.
  C3  Aalen-Johansen exacto (sin jitter) para CON VIDA / SIN VIDA.

Kaplan-Meier y Aalen-Johansen se calculan a mano, por día (la fuente no trae
hora), para que cada paso sea auditable. Toda aleatoriedad usa SEED.
"""
from __future__ import annotations

import sqlite3
import numpy as np
import pandas as pd

from .config import DB_PATH, OUTPUT_TABLES, CUTOFF_DATE

SEED = 42
HORIZONS = (1, 3, 7, 30)
M_IMPUTATIONS = 200
B_BOOTSTRAP = 1000
M_IN_BOOTSTRAP = 20
M_IN_GROUP_BOOTSTRAP = 10
MIN_EVENTS_GROUP = 30
CURVE_MAX_DAY = 60
GROUP_COLS = ("sex", "age_group", "borough_missing", "report_year", "report_source")
STATE = {"CON VIDA": 1, "SIN VIDA": 2}


# ---------------------------------------------------------------------------
# Datos y clasificación (C1, C2)
# ---------------------------------------------------------------------------
def load_classified(db_path=DB_PATH) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        v = pd.read_sql("SELECT * FROM vw_cases", conn)
    cut = pd.Timestamp(CUTOFF_DATE)
    v["rd"] = pd.to_datetime(v["report_date"])
    v["ld"] = pd.to_datetime(v["location_date"])
    reason = v["excluded_from_report_timeline_reason"]
    located = v["is_located"] == 1

    cls = np.select(
        [
            ~located,
            reason.eq("impossible_order"),
            reason.eq("ambiguous_pre_registration"),
            reason.eq("status_located_without_date"),
            located & reason.isna() & v["report_to_location_days"].notna(),
        ],
        ["ABIERTO", "IMPOSIBLE", "AMBIGUO", "SIN_FECHA", "VALIDO"],
        default="SIN_CLASE",
    )
    v["population_class"] = cls
    v["follow_up_days"] = (cut - v["rd"]).dt.days.astype(float)
    v["post_cutoff"] = (v["population_class"] == "VALIDO") & (v["ld"] > cut)
    v["report_year"] = v["rd"].dt.year.astype("Int64").astype(str)
    v["state"] = v["location_condition"].map(STATE).fillna(3).astype(int)
    return v


def scenario_arrays(v: pd.DataFrame, scenario: str):
    """Devuelve (mask, duraciones, eventos, estados) para E0, E1, E2-baja, E2-alta.
    E3 se arma en impute_e3(). Estados: 0 censura, 1 CON VIDA, 2 SIN VIDA, 3 desconocida."""
    c = v["population_class"]
    valid_ok = (c == "VALIDO") & ~v["post_cutoff"]
    dur = np.where(valid_ok, v["report_to_location_days"], v["follow_up_days"]).astype(float)
    ev = valid_ok.astype(int).to_numpy()
    st = np.where(valid_ok, v["state"], 0)

    mask = (c == "VALIDO") | (c == "ABIERTO")
    if scenario in ("E1", "E2-baja", "E2-alta", "E3"):
        amb = (c == "AMBIGUO").to_numpy()
        mask = mask | amb
        dur = np.where(amb, 0.0, dur)
        ev = np.where(amb, 1, ev)
        st = np.where(amb, v["state"], st)
    if scenario in ("E2-baja", "E2-alta", "E3"):
        nod = (c == "SIN_FECHA").to_numpy()
        mask = mask | nod
        if scenario == "E2-baja":
            dur = np.where(nod, 1e9, dur)
            ev = np.where(nod, 0, ev)
            st = np.where(nod, 0, st)
        elif scenario == "E2-alta":
            dur = np.where(nod, 0.0, dur)
            ev = np.where(nod, 1, ev)
            st = np.where(nod, v["state"], st)
    m = np.asarray(mask, bool)
    return m, dur[m], ev[m], st[m]


# ---------------------------------------------------------------------------
# Estimadores exactos por día
# ---------------------------------------------------------------------------
def _risk_table(dur, states):
    """Tiempos únicos, en riesgo y eventos por estado (vectorizado)."""
    t, inv = np.unique(dur, return_inverse=True)
    n_t = np.bincount(inv, minlength=len(t))
    at_risk = len(dur) - np.concatenate([[0], np.cumsum(n_t)[:-1]])
    d = {k: np.bincount(inv, weights=(states == k), minlength=len(t)) for k in (1, 2, 3)}
    return t, at_risk.astype(float), d


def km_curve(dur, ev):
    """Kaplan-Meier de 'localización documentada'. Devuelve (t, S)."""
    t, inv = np.unique(np.asarray(dur, float), return_inverse=True)
    n_t = np.bincount(inv, minlength=len(t))
    d_t = np.bincount(inv, weights=np.asarray(ev, float), minlength=len(t))
    at_risk = len(dur) - np.concatenate([[0], np.cumsum(n_t)[:-1]])
    S = np.cumprod(1 - d_t / at_risk)
    return t, S


def pct_at(t, S, horizons=HORIZONS):
    out = []
    for h in horizons:
        idx = np.searchsorted(t, h, side="right") - 1
        out.append(100 * (1 - S[idx]) if idx >= 0 else 0.0)
    return np.array(out)


def km_pct(dur, ev, horizons=HORIZONS):
    t, S = km_curve(dur, ev)
    return pct_at(t, S, horizons)


def aj_exact(dur, states):
    """Aalen-Johansen discreto. Devuelve (t, cif[3 x T], S). CIF_k(t) += S(t-) d_k/n."""
    t, n, d = _risk_table(np.asarray(dur, float), np.asarray(states, int))
    d_all = d[1] + d[2] + d[3]
    S = np.cumprod(1 - d_all / n)
    S_prev = np.concatenate([[1.0], S[:-1]])
    cif = np.vstack([np.cumsum(S_prev * d[k] / n) for k in (1, 2, 3)])
    return t, cif, S


def aj_at(t, cif, horizons=HORIZONS):
    out = np.zeros((3, len(horizons)))
    for j, h in enumerate(horizons):
        idx = np.searchsorted(t, h, side="right") - 1
        if idx >= 0:
            out[:, j] = 100 * cif[:, idx]
    return out


# ---------------------------------------------------------------------------
# E3: imputación múltiple de SIN_FECHA
# ---------------------------------------------------------------------------
def _e3_parts(v: pd.DataFrame):
    m, dur, ev, st = scenario_arrays(v, "E1")
    c = v["population_class"].to_numpy()
    nod = c == "SIN_FECHA"
    base = pd.DataFrame({
        "dur": np.concatenate([dur, np.full(nod.sum(), np.nan)]),
        "ev": np.concatenate([ev, np.zeros(nod.sum(), int)]),
        "st": np.concatenate([st, v.loc[nod, "state"].to_numpy()]),
        "fu": np.concatenate([v.loc[m, "follow_up_days"].to_numpy(), v.loc[nod, "follow_up_days"].to_numpy()]),
        "is_nod": np.concatenate([np.zeros(m.sum(), bool), np.ones(nod.sum(), bool)]),
        "case_idx": np.concatenate([np.where(m)[0], np.where(nod)[0]]),
    })
    return base


def _pool(base: pd.DataFrame) -> np.ndarray:
    """Duraciones observadas de localizados con fecha (VALIDO sin post-corte + AMBIGUO en 0)."""
    return base.loc[~base["is_nod"] & (base["ev"] == 1), "dur"].to_numpy()


def _impute_once(base: pd.DataFrame, pool: np.ndarray, rng):
    dur = base["dur"].to_numpy().copy()
    ev = base["ev"].to_numpy().copy()
    st = base["st"].to_numpy().copy()
    nod = base["is_nod"].to_numpy()
    fu = base["fu"].to_numpy()
    k = nod.sum()
    imp = rng.choice(pool, size=k, replace=True)
    over = imp > fu[nod]
    dur[nod] = np.where(over, fu[nod], imp)
    ev[nod] = np.where(over, 0, 1)
    st[nod] = np.where(over, 0, st[nod])
    return dur, ev, st


def e3_estimate(v: pd.DataFrame, M=M_IMPUTATIONS, seed=SEED):
    base = _e3_parts(v)
    pool = _pool(base)
    rng = np.random.default_rng(seed)
    km_res, aj_res, curves, cif_curves = [], [], [], []
    grid = np.arange(0, CURVE_MAX_DAY + 1)
    for _ in range(M):
        dur, ev, st = _impute_once(base, pool, rng)
        t, S = km_curve(dur, ev)
        km_res.append(pct_at(t, S))
        curves.append(pct_at(t, S, grid))
        ta, cif, _ = aj_exact(dur, st)
        aj_res.append(aj_at(ta, cif))
        cif_curves.append(aj_at(ta, cif, grid))
    return {
        "n": len(base), "pool_size": len(pool),
        "km": np.mean(km_res, axis=0),
        "km_imp_lo": np.percentile(km_res, 2.5, axis=0),
        "km_imp_hi": np.percentile(km_res, 97.5, axis=0),
        "curve": np.mean(curves, axis=0),
        "aj": np.mean(aj_res, axis=0),
        "cif_curve": np.mean(cif_curves, axis=0),
    }


def bootstrap_e3(v: pd.DataFrame, B=B_BOOTSTRAP, M=M_IN_BOOTSTRAP, seed=SEED, curve=True):
    """IC 95%: remuestreo de casos; dentro de cada réplica se recalcula el pool
    y se imputa M veces."""
    base = _e3_parts(v)
    rng = np.random.default_rng(seed)
    grid = np.arange(0, CURVE_MAX_DAY + 1)
    km_b, aj_b, curve_b = [], [], []
    n = len(base)
    for _ in range(B):
        bs = base.iloc[rng.integers(0, n, n)].reset_index(drop=True)
        pool = _pool(bs)
        km_m, aj_m, cu_m = [], [], []
        for _ in range(M):
            dur, ev, st = _impute_once(bs, pool, rng)
            t, S = km_curve(dur, ev)
            km_m.append(pct_at(t, S))
            if curve:
                cu_m.append(pct_at(t, S, grid))
            ta, cif, _ = aj_exact(dur, st)
            aj_m.append(aj_at(ta, cif))
        km_b.append(np.mean(km_m, axis=0))
        aj_b.append(np.mean(aj_m, axis=0))
        if curve:
            curve_b.append(np.mean(cu_m, axis=0))
    out = {
        "km_lo": np.percentile(km_b, 2.5, axis=0), "km_hi": np.percentile(km_b, 97.5, axis=0),
        "aj_lo": np.percentile(aj_b, 2.5, axis=0), "aj_hi": np.percentile(aj_b, 97.5, axis=0),
    }
    if curve:
        out["curve_lo"] = np.percentile(curve_b, 2.5, axis=0)
        out["curve_hi"] = np.percentile(curve_b, 97.5, axis=0)
    return out


def bootstrap_deterministic(dur, ev, st, B=B_BOOTSTRAP, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(dur)
    km_b, aj_b = [], []
    for _ in range(B):
        i = rng.integers(0, n, n)
        km_b.append(km_pct(dur[i], ev[i]))
        ta, cif, _ = aj_exact(dur[i], st[i])
        aj_b.append(aj_at(ta, cif))
    return (np.percentile(km_b, 2.5, axis=0), np.percentile(km_b, 97.5, axis=0),
            np.percentile(aj_b, 2.5, axis=0), np.percentile(aj_b, 97.5, axis=0))


# ---------------------------------------------------------------------------
# Exportes v0.2
# ---------------------------------------------------------------------------
def _save(df: pd.DataFrame, name: str) -> pd.DataFrame:
    df.to_csv(OUTPUT_TABLES / name, index=False, encoding="utf-8-sig")
    return df


def export_population_classes(v: pd.DataFrame) -> pd.DataFrame:
    counts = v["population_class"].value_counts()
    order = ["VALIDO", "AMBIGUO", "SIN_FECHA", "IMPOSIBLE", "ABIERTO", "SIN_CLASE"]
    desc = {
        "VALIDO": "Localizado con duración reporte→localización válida",
        "AMBIGUO": "Localizado antes de que se registrara el reporte (día 0 desde E1)",
        "SIN_FECHA": "Estatus LOCALIZADO sin fecha utilizable (imputado en E3)",
        "IMPOSIBLE": "Localización anterior a la desaparición (excluido de todo)",
        "ABIERTO": "Estatus DESAPARECIDO al corte (censurado)",
        "SIN_CLASE": "No clasificado (debe ser 0)",
    }
    rows = [{"clase": k, "n": int(counts.get(k, 0)),
             "pct": round(100 * counts.get(k, 0) / len(v), 2), "descripcion": desc[k]}
            for k in order]
    _save(v.loc[v["post_cutoff"], ["case_key", "report_date", "location_date", "status"]],
          "post_cutoff_cases_v02.csv")
    return _save(pd.DataFrame(rows), "population_classes_v02.csv")


def export_scenarios(v: pd.DataFrame, e3: dict, e3_boot: dict) -> pd.DataFrame:
    rows = []
    for sc in ("E0", "E1", "E2-baja", "E2-alta"):
        _, dur, ev, st = scenario_arrays(v, sc)
        pct = km_pct(dur, ev)
        lo, hi, _, _ = bootstrap_deterministic(dur, ev, st)
        for j, h in enumerate(HORIZONS):
            rows.append({"escenario": sc, "horizonte": h, "pct": round(pct[j], 2),
                         "ic_baja": round(lo[j], 2), "ic_alta": round(hi[j], 2), "n": len(dur),
                         "imp_baja": None, "imp_alta": None})
    for j, h in enumerate(HORIZONS):
        rows.append({"escenario": "E3", "horizonte": h, "pct": round(e3["km"][j], 2),
                     "ic_baja": round(e3_boot["km_lo"][j], 2), "ic_alta": round(e3_boot["km_hi"][j], 2),
                     "n": e3["n"], "imp_baja": round(e3["km_imp_lo"][j], 2),
                     "imp_alta": round(e3["km_imp_hi"][j], 2)})
    return _save(pd.DataFrame(rows), "km_scenarios_v02.csv")


def export_curve_e3(e3: dict, e3_boot: dict) -> pd.DataFrame:
    grid = np.arange(0, CURVE_MAX_DAY + 1)
    return _save(pd.DataFrame({
        "t": grid, "pct_localizado": np.round(e3["curve"], 2),
        "ic_baja": np.round(e3_boot["curve_lo"], 2), "ic_alta": np.round(e3_boot["curve_hi"], 2),
    }), "km_curve_e3_v02.csv")


def export_cif(v: pd.DataFrame, e3: dict, e3_boot: dict) -> pd.DataFrame:
    grid = np.arange(0, CURVE_MAX_DAY + 1)
    _, dur, ev, st = scenario_arrays(v, "E0")
    ta, cif, S = aj_exact(dur, st)
    c0 = aj_at(ta, cif, grid)
    tk, Sk = km_curve(dur, ev)
    k0 = pct_at(tk, Sk, grid)
    curve_rows = []
    for name, cc, kk in (("E0", c0, k0), ("E3", e3["cif_curve"], None)):
        for i, t in enumerate(grid):
            curve_rows.append({"poblacion": name, "t": int(t),
                               "con_vida": round(cc[0, i], 2), "sin_vida": round(cc[1, i], 2),
                               "desconocida": round(cc[2, i], 2), "suma": round(cc[:, i].sum(), 2),
                               "km": round(kk[i], 2) if kk is not None else round(e3["curve"][i], 2)})
    _save(pd.DataFrame(curve_rows), "cif_exact_v02.csv")

    _, _, aj_lo0, aj_hi0 = bootstrap_deterministic(dur, ev, st)
    aj0 = aj_at(ta, cif)
    rows = []
    names = ["CON VIDA", "SIN VIDA", "DESCONOCIDA"]
    for pop, est, lo, hi in (("E0", aj0, aj_lo0, aj_hi0), ("E3", e3["aj"], e3_boot["aj_lo"], e3_boot["aj_hi"])):
        for k in range(3):
            for j, h in enumerate(HORIZONS):
                rows.append({"poblacion": pop, "desenlace": names[k], "horizonte": h,
                             "cif_pct": round(est[k, j], 2), "ic_baja": round(lo[k, j], 2),
                             "ic_alta": round(hi[k, j], 2)})
    return _save(pd.DataFrame(rows), "cif_summary_v02.csv")


def export_naive_vs_exact(db_path=DB_PATH) -> pd.DataFrame:
    """Sobre la población ORIGINAL de la versión 79 (vw_outcome_competing_risk_input,
    corte del proyecto) para medir solo el efecto del método, no de la población."""
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql("SELECT * FROM vw_outcome_competing_risk_input", conn)
        cut = pd.read_sql("""SELECT MAX(dt) AS m FROM (SELECT MAX(report_date) AS dt FROM vw_cases
                             UNION ALL SELECT MAX(location_date) FROM vw_cases)""", conn)["m"][0]
    dur = np.where(df["event_type"] > 0, df["report_to_location_days"],
                   (pd.Timestamp(cut) - pd.to_datetime(df["report_date"])).dt.days).astype(float)
    st = df["event_type"].to_numpy().astype(int)
    ta, cif, _ = aj_exact(dur, st)
    exact = aj_at(ta, cif)
    naive = km_pct(dur, (st == 2).astype(int))
    rows = [{"horizonte": h, "sin_vida_ingenuo": round(naive[j], 2),
             "sin_vida_exacto": round(exact[1, j], 2),
             "sobreestimacion_rel_pct": round(100 * (naive[j] / exact[1, j] - 1), 1),
             "con_vida_exacto": round(exact[0, j], 2), "desconocida_exacto": round(exact[2, j], 2),
             "suma_exacta": round(exact[:, j].sum(), 2), "km_cualquiera": round(km_pct(dur, (st > 0).astype(int))[j], 2),
             "n": len(dur), "poblacion": "ORIGINAL v79 (2,394; corte del proyecto)"}
            for j, h in enumerate(HORIZONS)]
    return _save(pd.DataFrame(rows), "naive_vs_exact_v02.csv")


def export_group_kpis(v: pd.DataFrame, B=B_BOOTSTRAP, M_point=M_IMPUTATIONS,
                      M_boot=M_IN_GROUP_BOOTSTRAP, seed=SEED) -> pd.DataFrame:
    base = _e3_parts(v)
    pool_global = _pool(base)
    case_vals = v.iloc[base["case_idx"].to_numpy()].reset_index(drop=True)
    rng = np.random.default_rng(seed)
    rows = []
    for col in GROUP_COLS:
        vals = case_vals[col].fillna("SIN DATO").astype(str)
        for val in sorted(vals.unique()):
            g = (vals == val).to_numpy()
            sub = base[g].reset_index(drop=True)
            events_obs = int(((~sub["is_nod"]) & (sub["ev"] == 1)).sum())
            pts = [km_pct(*_impute_once(sub, pool_global, rng)[:2])[1] for _ in range(M_point)]
            boots = []
            n = len(sub)
            for _ in range(B):
                bs = sub.iloc[rng.integers(0, n, n)].reset_index(drop=True)
                boots.append(np.mean([km_pct(*_impute_once(bs, pool_global, rng)[:2])[1]
                                      for _ in range(M_boot)]))
            rows.append({"grupo": col, "valor": val, "n_riesgo": n,
                         "eventos_observados": events_obs,
                         "pct_le3d_e3": round(float(np.mean(pts)), 2),
                         "ic_baja": round(float(np.percentile(boots, 2.5)), 2),
                         "ic_alta": round(float(np.percentile(boots, 97.5)), 2),
                         "pct_sin_fecha": round(100 * sub["is_nod"].mean(), 2),
                         "below_min_sample_size": int(events_obs < MIN_EVENTS_GROUP)})
    return _save(pd.DataFrame(rows), "group_kpis_v02.csv")


def export_outcome_intervals_v02(v: pd.DataFrame) -> pd.DataFrame:
    """Desenlace por intervalo reporte→localización con la clasificación v0.2.

    Solo la clase VALIDO (1,211 casos): excluye los localizados con fecha anterior
    a la desaparición (IMPOSIBLE), que la tabla v0.1 (outcome_intervals_report_clock)
    todavía contaba. Mismos cortes y columnas que la tabla v0.1.
    """
    c = v[v["population_class"] == "VALIDO"]
    days = c["report_to_location_days"].astype(float)
    labels = ["≤1 día", ">1-3 días", ">3-7 días", ">7-30 días", ">30 días"]
    bucket = pd.cut(days, [-np.inf, 1, 3, 7, 30, np.inf], labels=labels)
    cond = c["location_condition"].fillna("DESCONOCIDA")
    pivot = pd.crosstab(bucket, cond).reindex(index=labels, columns=["CON VIDA", "SIN VIDA", "DESCONOCIDA"], fill_value=0)
    pivot["total"] = pivot.sum(axis=1)
    for col in ["CON VIDA", "SIN VIDA", "DESCONOCIDA"]:
        tot = pivot[col].sum()
        pivot[f"pct_{col.replace(' ', '_')}"] = (100 * pivot[col] / tot if tot else np.nan).round(2)
    pivot["pct_sin_vida_del_intervalo"] = (100 * pivot["SIN VIDA"] / pivot["total"]).round(2)
    pivot.index.name = "intervalo"
    return _save(pivot.reset_index(), "outcome_intervals_v02.csv")


def run_v02(db_path=DB_PATH) -> dict:
    v = load_classified(db_path)
    export_population_classes(v)
    export_outcome_intervals_v02(v)
    e3 = e3_estimate(v)
    e3_boot = bootstrap_e3(v)
    export_scenarios(v, e3, e3_boot)
    export_curve_e3(e3, e3_boot)
    export_cif(v, e3, e3_boot)
    export_group_kpis(v)
    return {"v": v, "e3": e3, "e3_boot": e3_boot}
