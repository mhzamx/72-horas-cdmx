"""Genera el proyecto Power BI (PBIP) de 72 HORAS v0.2 a partir de outputs/tables.

Uso:  python powerbi/build_pbip_72h.py [ruta_windows_del_excel]
Salida (carpeta powerbi/):
  72H_PowerBI_model_v02.xlsx      tablas AGREGADAS (sin datos por caso: se puede compartir)
  72HORAS_v02.pbip + .Report/ + .SemanticModel/
Abrir 72HORAS_v02.pbip en Power BI Desktop -> Inicio > Actualizar -> Archivo > Guardar como .pbix.
Formato tomado de un PBIP guardado por Power BI Desktop (proyecto P2 Food Resilience).
"""
from __future__ import annotations
import json, shutil, sys, uuid
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "outputs" / "tables"
OUT = ROOT / "powerbi"
NAME = "72HORAS_v02"
XLSX = "72H_PowerBI_model_v02.xlsx"
DEFAULT_WIN_PATH = r"C:\Users\Miguel\Documents\72-horas-v0.2\powerbi" + "\\" + XLSX
BLUE, ORANGE, GREY, INK, INK2, BG = "#2A78D6", "#EB6834", "#9AA5B1", "#0B0B0B", "#52514E", "#FCFCFB"
U = lambda: str(uuid.uuid4())
NOTE = ("Fuente: CBPCDMX, Registro Interno (reportes 25-jun-2019 a 14-nov-2022; corte 15-nov-2022). "
        "Solo fechas, sin hora: 72 h = ≤3 días calendario. 72 horas es un hito de medición, no un plazo de espera: la búsqueda es inmediata.")


# ---------------------------------------------------------------- datos
def build_tables() -> dict[str, pd.DataFrame]:
    r = lambda n: pd.read_csv(T / n, encoding="utf-8-sig")
    sc = r("km_scenarios_v02.csv")
    lab = {"E0": "E0 · versión publicada", "E1": "E1 · + localizados antes del registro",
           "E2-baja": "E2-baja · sin fecha = no localizados", "E3": "E3 · PRINCIPAL (sin fecha imputados)",
           "E2-alta": "E2-alta · sin fecha = día 0"}
    order = {"E0": 1, "E1": 2, "E2-baja": 3, "E3": 4, "E2-alta": 5}
    sc["escenario_label"] = sc["escenario"].map(lab)
    sc["orden"] = sc["escenario"].map(order)
    sc3 = sc[sc["horizonte"] == 3].copy()
    curve = r("km_curve_e3_v02.csv"); curve = curve[curve["t"] <= 30]
    cif = r("cif_exact_v02.csv"); cif = cif[(cif["poblacion"] == "E3") & (cif["t"] <= 30)]
    cifs = r("cif_summary_v02.csv")
    g = r("group_kpis_v02.csv")
    g = g[g["below_min_sample_size"] == 0].copy()
    out = {}
    for key, col in (("grp_sexo", "sex"), ("grp_edad", "age_group"), ("grp_anio", "report_year"),
                     ("grp_fuente", "report_source"), ("grp_alcaldia", "borough_missing")):
        d = g[g["grupo"] == col].copy()
        if key != "grp_alcaldia":
            d = d[d["valor"] != "SIN DATO"]
        d["valor"] = d["valor"].replace({"SIN DATO": "SIN ALCALDÍA REGISTRADA"}).astype(str).str.title()
        d["orden"] = range(1, len(d) + 1)
        out[key] = d[["valor", "orden", "n_riesgo", "eventos_observados", "pct_le3d_e3", "ic_baja", "ic_alta", "pct_sin_fecha"]]
    pc = r("population_classes_v02.csv"); pc = pc[pc["clase"] != "SIN_CLASE"].copy()
    pc["orden"] = range(1, len(pc) + 1)
    dq = r("data_quality_summary.csv")
    oi = r("outcome_intervals_report_clock.csv")
    oi = oi.rename(columns={"CON VIDA": "con_vida", "SIN VIDA": "sin_vida", "DESCONOCIDA": "desconocida"})
    oi["orden"] = range(1, len(oi) + 1)
    out.update({"km_scenarios": sc[["escenario", "escenario_label", "orden", "horizonte", "pct", "ic_baja", "ic_alta", "n"]],
                "km_scenarios_3d": sc3[["escenario", "escenario_label", "orden", "pct", "ic_baja", "ic_alta", "n"]],
                "km_curve_e3": curve, "cif_e3": cif[["t", "con_vida", "sin_vida", "desconocida", "km"]],
                "cif_summary": cifs, "population_classes": pc, "data_quality": dq,
                "outcome_intervals": oi[["intervalo", "orden", "con_vida", "sin_vida", "desconocida", "total", "pct_sin_vida_del_intervalo"]]})
    return out


SORT_BY = {"km_scenarios": {"escenario_label": "orden"}, "km_scenarios_3d": {"escenario_label": "orden"},
           "grp_edad": {"valor": "orden"}, "grp_anio": {"valor": "orden"}, "population_classes": {"clase": "orden"},
           "outcome_intervals": {"intervalo": "orden"}}


def _dtype(s: pd.Series):
    if pd.api.types.is_integer_dtype(s):
        return "int64", "Int64.Type", "0"
    if pd.api.types.is_float_dtype(s):
        return "double", "type number", "0.00"
    return "string", "type text", None


def table_tmdl(name: str, df: pd.DataFrame) -> str:
    cols, types = [], []
    for c in df.columns:
        dt, mt, fmt = _dtype(df[c])
        hidden = "\t\tisHidden\n" if c == "orden" else ""
        f = f"\t\tformatString: {fmt}\n" if fmt else ""
        sb = f"\t\tsortByColumn: {SORT_BY[name][c]}\n" if c in SORT_BY.get(name, {}) else ""
        cols.append(f"\tcolumn {c}\n\t\tdataType: {dt}\n{hidden}{f}\t\tlineageTag: {U()}\n\t\tsummarizeBy: none\n"
                    f"\t\tsourceColumn: {c}\n{sb}\n\t\tannotation SummarizationSetBy = Automatic\n")
        types.append('{"%s", %s}' % (c, mt))
    m = ("\t\t\t\tlet\n"
         "\t\t\t\t    Source = Excel.Workbook(File.Contents(ExcelPath), null, true),\n"
         f"\t\t\t\t    Sheet = Source{{[Item=\"{name}\",Kind=\"Sheet\"]}}[Data],\n"
         "\t\t\t\t    Promoted = Table.PromoteHeaders(Sheet, [PromoteAllScalars=true]),\n"
         f"\t\t\t\t    Typed = Table.TransformColumnTypes(Promoted,{{{', '.join(types)}}})\n"
         "\t\t\t\tin\n\t\t\t\t    Typed")
    return (f"table {name}\n\tlineageTag: {U()}\n\n" + "\n".join(cols) +
            f"\n\tpartition {name} = m\n\t\tmode: import\n\t\tsource =\n{m}\n\n\tannotation PBI_ResultType = Table\n\n")


MEASURES = [  # (nombre, DAX, formato, carpeta)
    ("Casos recibidos", "SUM ( population_classes[n] )", "#,0", "1 Tarjetas"),
    ("% localizado ≤3 días (E3)", 'CALCULATE ( SUM ( km_scenarios[pct] ), km_scenarios[escenario] = "E3", km_scenarios[horizonte] = 3 ) / 100', "0.0%", "1 Tarjetas"),
    ("IC y rango E3", 'VAR lo = CALCULATE ( SUM ( km_scenarios[ic_baja] ), km_scenarios[escenario] = "E3", km_scenarios[horizonte] = 3 ) / 100\n'
     '\t\t\tVAR hi = CALCULATE ( SUM ( km_scenarios[ic_alta] ), km_scenarios[escenario] = "E3", km_scenarios[horizonte] = 3 ) / 100\n'
     '\t\t\tVAR rb = CALCULATE ( SUM ( km_scenarios[pct] ), km_scenarios[escenario] = "E2-baja", km_scenarios[horizonte] = 3 ) / 100\n'
     '\t\t\tVAR ra = CALCULATE ( SUM ( km_scenarios[pct] ), km_scenarios[escenario] = "E2-alta", km_scenarios[horizonte] = 3 ) / 100\n'
     '\t\t\tVAR pt = CALCULATE ( SUM ( km_scenarios[pct] ), km_scenarios[escenario] = "E3", km_scenarios[horizonte] = 3 ) / 100\n'
     '\t\t\tRETURN "Estimación principal ≤3 días (E3): " & FORMAT ( pt, "0.0%" ) & "  ·  IC 95%: " & FORMAT ( lo, "0.0%" ) & "–" & FORMAT ( hi, "0.0%" ) & "  ·  Rango por fechas faltantes: " & FORMAT ( rb, "0.0%" ) & "–" & FORMAT ( ra, "0.0%" )', None, "1 Tarjetas"),
    ("Cifra publicada antes (E0)", 'CALCULATE ( SUM ( km_scenarios[pct] ), km_scenarios[escenario] = "E0", km_scenarios[horizonte] = 3 ) / 100', "0.0%", "1 Tarjetas"),
    ("Abiertos al corte", 'CALCULATE ( SUM ( population_classes[n] ), population_classes[clase] = "ABIERTO" )', "#,0", "1 Tarjetas"),
    ("Sin vida ≤30 días (E3)", 'CALCULATE ( SUM ( cif_summary[cif_pct] ), cif_summary[poblacion] = "E3", cif_summary[desenlace] = "SIN VIDA", cif_summary[horizonte] = 30 ) / 100', "0.0%", "1 Tarjetas"),
    ("Localización acumulada (E3)", "SUM ( km_curve_e3[pct_localizado] ) / 100", "0.0%", "2 Series"),
    ("IC 95% inferior", "SUM ( km_curve_e3[ic_baja] ) / 100", "0.0%", "2 Series"),
    ("IC 95% superior", "SUM ( km_curve_e3[ic_alta] ) / 100", "0.0%", "2 Series"),
    ("% ≤3 días por escenario", "SUM ( km_scenarios_3d[pct] ) / 100", "0.0%", "2 Series"),
    ("Con vida", "SUM ( cif_e3[con_vida] ) / 100", "0.0%", "2 Series"),
    ("Sin vida", "SUM ( cif_e3[sin_vida] ) / 100", "0.0%", "2 Series"),
    ("Sexo · % ≤3 días", "SUM ( grp_sexo[pct_le3d_e3] ) / 100", "0.0%", "3 Grupos"),
    ("Edad · % ≤3 días", "SUM ( grp_edad[pct_le3d_e3] ) / 100", "0.0%", "3 Grupos"),
    ("Año · % ≤3 días", "SUM ( grp_anio[pct_le3d_e3] ) / 100", "0.0%", "3 Grupos"),
    ("Fuente · % ≤3 días", "SUM ( grp_fuente[pct_le3d_e3] ) / 100", "0.0%", "3 Grupos"),
    ("Alcaldía · % ≤3 días", "SUM ( grp_alcaldia[pct_le3d_e3] ) / 100", "0.0%", "3 Grupos"),
    ("Casos por clase", "SUM ( population_classes[n] )", "#,0", "4 Calidad"),
]


def measures_tmdl() -> str:
    body = []
    for n, dax, fmt, folder in MEASURES:
        expr = f" = {dax}" if "\n" not in dax else f" =\n\t\t\t{dax}"
        f = f"\t\tformatString: {fmt}\n" if fmt else ""
        body.append(f"\tmeasure '{n}'{expr}\n{f}\t\tdisplayFolder: {folder}\n\t\tlineageTag: {U()}\n")
    return (f"table _Measures\n\tlineageTag: {U()}\n\n" + "\n".join(body) +
            f"\n\tcolumn Column1\n\t\tdataType: string\n\t\tisHidden\n\t\tlineageTag: {U()}\n\t\tsummarizeBy: none\n"
            "\t\tsourceColumn: Column1\n\n\tpartition _Measures = m\n\t\tmode: import\n"
            "\t\tsource = Table.FromRecords({[Column1 = \"\"]})\n\n\tannotation PBI_ResultType = Table\n\n")


# ---------------------------------------------------------------- visuales
L = lambda v: {"expr": {"Literal": {"Value": v}}}
COLOR = lambda c: {"solid": {"color": L(f"'{c}'")}}
SCHEMA_V = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json"
_vid = iter(range(1, 10_000))


def _container(vtype, x, y, w, h, alt, query=None, objects=None, title=None):
    name = f"v{next(_vid):04d}" + uuid.uuid4().hex[:15]
    vco = {"background": [{"properties": {"show": L("false")}}], "border": [{"properties": {"show": L("false")}}],
           "dropShadow": [{"properties": {"show": L("false")}}],
           "general": [{"properties": {"altText": L(f"'{alt}'")}}]}
    if title:
        vco["title"] = [{"properties": {"show": L("true"), "text": L(f"'{title}'"), "fontColor": COLOR(INK),
                                        "fontSize": L("12D")}}]
    else:
        vco["title"] = [{"properties": {"show": L("false")}}]
    vis = {"visualType": vtype, **({"query": query} if query else {}), **({"objects": objects} if objects else {}),
           "visualContainerObjects": vco, "drillFilterOtherVisuals": True}
    z = next(_vid) * 100
    return name, {"$schema": SCHEMA_V, "name": name,
                  "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z}, "visual": vis}


def textbox(x, y, w, h, runs, alt="Texto"):
    paras = [{"textRuns": [{"value": t, "textStyle": {"fontFamily": "Segoe UI", "fontSize": f"{s}pt", "color": c,
                                                        **({"fontWeight": "bold"} if b else {})}}]} for t, s, c, b in runs]
    return _container("textbox", x, y, w, h, alt, objects={"general": [{"properties": {"paragraphs": paras}}]})


def _m(n, disp=None):
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": n}},
            "queryRef": f"_Measures.{n}", "nativeQueryRef": disp or n, "displayName": disp or n}


def _c(t, c, disp=None, active=False):
    p = {"field": {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}},
         "queryRef": f"{t}.{c}", "nativeQueryRef": disp or c, "displayName": disp or c}
    if active:
        p["active"] = True
    return p


def card(x, y, w, h, measure, label, font=28, show_label=True):
    obj = {"labels": [{"properties": {"color": COLOR(INK), "fontSize": L(f"{font}D")}}],
           "categoryLabels": [{"properties": {"show": L("true" if show_label else "false"), "color": COLOR(INK2), "fontSize": L("10D")}}]}
    return _container("card", x, y, w, h, f"Tarjeta: {label}", {"queryState": {"Values": {"projections": [_m(measure, label)]}}}, obj)


def chart(vtype, x, y, w, h, table, cat, cat_disp, measures, title, colors, alt, sort_cat=True, labels=True, y0=False):
    q = {"queryState": {"Category": {"projections": [_c(table, cat, cat_disp, True)]},
                        "Y": {"projections": [_m(m, d) for m, d in measures]}}}
    if sort_cat:
        q["sortDefinition"] = {"sort": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": cat}},
                                         "direction": "Ascending"}]}
    obj = {"legend": [{"properties": {"show": L("true" if len(measures) > 1 else "false"), "position": L("'Top'")}}],
           "categoryAxis": [{"properties": {"showAxisTitle": L("false"), "labelColor": COLOR(INK2)}}],
           "valueAxis": [{"properties": {"showAxisTitle": L("false"), "labelColor": COLOR(INK2), **({"start": L("0D")} if y0 else {})}}],
           "dataPoint": [{"properties": {"fill": COLOR(c)}, "selector": {"metadata": f"_Measures.{m}"}}
                         for (m, _), c in zip(measures, colors)],
           "labels": [{"properties": {"show": L("true" if labels else "false"), "color": COLOR(INK), "fontSize": L("9D")}}]}
    return _container(vtype, x, y, w, h, alt, q, obj, title)


def table_visual(x, y, w, h, table, cols, title, alt, font=9):
    # fuente compacta: todas las filas deben caber sin scroll (el PDF exporta el estado sin desplazar)
    q = {"queryState": {"Values": {"projections": [_c(table, c, d) for c, d in cols]}}}
    obj = {"values": [{"properties": {"fontSize": L(f"{font}D")}}], "columnHeaders": [{"properties": {"fontSize": L(f"{font}D")}}]}
    return _container("tableEx", x, y, w, h, alt, q, obj, title)


def pages() -> list[tuple[str, list]]:
    P = []
    hdr = lambda t, s: [textbox(24, 8, 1232, 44, [(t, 20, INK, True)], "Título"),
                        textbox(24, 52, 1232, 30, [(s, 10, INK2, False)], "Subtítulo")]
    foot = textbox(24, 690, 1232, 24, [(NOTE, 8, INK2, False)], "Nota de fuente")
    # 1. Resumen
    v = hdr("72 HORAS · Localización documentada desde el reporte (CBPCDMX 2019–2022)",
            "¿Qué proporción de los casos recibidos tiene localización documentada dentro de los 3 días posteriores al reporte?")
    v += [card(24, 86, 290, 100, "Casos recibidos", "Casos recibidos"),
          card(330, 86, 290, 100, "% localizado ≤3 días (E3)", "Localización documentada ≤3 días"),
          card(636, 86, 290, 100, "Abiertos al corte", "Seguían abiertos al corte"),
          card(942, 86, 314, 100, "Sin vida ≤30 días (E3)", "Localizados sin vida ≤30 días"),
          card(24, 188, 1232, 60, "IC y rango E3", "Incertidumbre", font=12, show_label=False),
          chart("lineChart", 24, 256, 820, 428, "km_curve_e3", "t", "Días desde el reporte",
                [("Localización acumulada (E3)", "E3 (principal)"), ("IC 95% inferior", "IC 95% inferior"), ("IC 95% superior", "IC 95% superior")],
                "Localización documentada acumulada, 0–30 días", [BLUE, GREY, GREY], "Línea: localización acumulada E3", labels=False, y0=True),
          textbox(866, 262, 390, 420, [
              ("Cómo leer", 13, INK, True),
              ("44% de los casos recibidos tenía localización documentada a ≤3 días del reporte. La versión publicada antes decía 34% porque excluía 564 casos localizados.", 10, INK, False),
              ("El rango (38.5%–46.2%) muestra cuánto cambia la cifra según cómo se traten 227 casos marcados como localizados sin fecha.", 10, INK, False),
              ("Abiertos al corte no significa que sigan desaparecidos hoy: el extracto no distingue desaparición prolongada de estatus no actualizado.", 10, INK, False),
              ("La fecha de localización es cierre administrativo, no fecha de fallecimiento. Nada aquí es causal.", 10, INK2, False)], "Panel de lectura"),
          foot]
    P.append(("Resumen 72 horas", v))
    # 2. Sensibilidad
    v = hdr("¿Cuánto cambia la cifra según cómo se tratan los datos?",
            "% con localización documentada ≤3 días por escenario (S1). E3 es la estimación principal; E2-baja y E2-alta son las cotas.")
    v += [chart("clusteredColumnChart", 24, 86, 760, 590, "km_scenarios_3d", "escenario_label", "Escenario",
                [("% ≤3 días por escenario", "% ≤3 días")], None, [BLUE], "Columnas: escenarios E0 a E2-alta"),
          table_visual(800, 86, 456, 590, "km_scenarios", [("escenario", "Escenario"), ("horizonte", "Días"), ("pct", "%"),
                                                           ("ic_baja", "IC inf."), ("ic_alta", "IC sup."), ("n", "n")],
                       "Todos los horizontes (IC 95% bootstrap)", "Tabla de escenarios", font=8), foot]
    P.append(("Sensibilidad", v))
    # 3. Con vida / sin vida
    v = hdr("Desenlace registrado al localizar: con vida / sin vida (S2)",
            "Incidencia acumulada (Aalen-Johansen exacto) sobre la población E3. Fecha = cierre administrativo, NO fecha de fallecimiento.")
    v += [chart("lineChart", 24, 86, 760, 590, "cif_e3", "t", "Días desde el reporte",
                [("Con vida", "Con vida"), ("Sin vida", "Sin vida")], "Incidencia acumulada por desenlace, 0–30 días",
                [BLUE, ORANGE], "Línea: con vida y sin vida", labels=False, y0=True),
          table_visual(800, 86, 456, 590, "outcome_intervals", [("intervalo", "Intervalo"), ("con_vida", "Con vida"),
                                                               ("sin_vida", "Sin vida"), ("desconocida", "Desc."),
                                                               ("pct_sin_vida_del_intervalo", "% sin vida")],
                       "Localizados con fecha válida, por intervalo", "Tabla por intervalo"), foot]
    P.append(("Con vida y sin vida", v))
    # 4. Características
    v = hdr("Características asociadas con la localización (S3) · asociación, no causa",
            "% con localización documentada ≤3 días (E3) por grupo. Solo grupos con ≥30 localizaciones observadas.")
    specs = [("grp_sexo", "Sexo · % ≤3 días", "Sexo", 24, 86), ("grp_edad", "Edad · % ≤3 días", "Grupo de edad", 640, 86),
             ("grp_anio", "Año · % ≤3 días", "Año de reporte", 24, 388), ("grp_fuente", "Fuente · % ≤3 días", "Fuente del reporte", 640, 388)]
    for t, m, ttl, x, y in specs:
        v.append(chart("clusteredBarChart", x, y, 616, 292, t, "valor", ttl, [(m, "% ≤3 días")], ttl, [BLUE], f"Barras: {ttl}"))
    v.append(foot)
    P.append(("Características", v))
    # 5. Alcaldía y calidad
    v = hdr("Alcaldía y calidad del registro",
            "Alcaldías con IC traslapados: no se presenta ranking (orden alfabético). Las clases explican qué entra en cada estimación.")
    v += [chart("clusteredBarChart", 24, 86, 616, 590, "grp_alcaldia", "valor", "Alcaldía", [("Alcaldía · % ≤3 días", "% ≤3 días")],
                "Alcaldía de la desaparición · % ≤3 días (E3)", [BLUE], "Barras: alcaldías"),
          chart("clusteredBarChart", 656, 86, 600, 230, "population_classes", "clase", "Clase", [("Casos por clase", "Casos")],
                "Clases de población (2,958 casos)", [GREY], "Barras: clases de población"),
          table_visual(656, 326, 600, 350, "data_quality", [("check", "Regla"), ("category", "Categoría"),
                                                           ("affected_rows", "Casos"), ("pct_rows", "%")],
                       "Reglas de calidad del registro", "Tabla de calidad"), foot]
    P.append(("Alcaldía y calidad", v))
    return P


# ---------------------------------------------------------------- escritura
def write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def main(win_xlsx: str = DEFAULT_WIN_PATH, base_theme: Path | None = None) -> Path:
    OUT.mkdir(exist_ok=True)
    tables = build_tables()
    with pd.ExcelWriter(OUT / XLSX) as xw:
        for n, df in tables.items():
            df.to_excel(xw, sheet_name=n, index=False)
    rep, sm = OUT / f"{NAME}.Report", OUT / f"{NAME}.SemanticModel"
    for d in (rep, sm):
        if d.exists():
            shutil.rmtree(d)
    write(OUT / f"{NAME}.pbip", {"version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                                 "settings": {"enableAutoRecovery": True}})
    plat = lambda t: {"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                      "metadata": {"type": t, "displayName": NAME}, "config": {"version": "2.0", "logicalId": U()}}
    # modelo semántico
    write(sm / ".platform", plat("SemanticModel"))
    write(sm / "definition.pbism", {"version": "4.2", "settings": {}})
    write(sm / "definition" / "database.tmdl", "database\n\tcompatibilityLevel: 1606\n\n")
    names = list(tables) + ["_Measures"]
    write(sm / "definition" / "model.tmdl",
          "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tsourceQueryCulture: en-US\n"
          "\tdataAccessOptions\n\t\tlegacyRedirects\n\t\treturnErrorValuesAsNull\n\n"
          "annotation __PBI_TimeIntelligenceEnabled = 0\n\n"
          f"annotation PBI_QueryOrder = {json.dumps(['ExcelPath'] + names, ensure_ascii=False)}\n\n"
          + "".join(f"ref table {n}\n" for n in names) + "\n")
    write(sm / "definition" / "expressions.tmdl",
          f'expression ExcelPath = "{win_xlsx}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]\n'
          f"\tlineageTag: {U()}\n\n\tannotation PBI_NavigationStepName = Navigation\n\n\tannotation PBI_ResultType = Text\n\n")
    for n, df in tables.items():
        write(sm / "definition" / "tables" / f"{n}.tmdl", table_tmdl(n, df))
    write(sm / "definition" / "tables" / "_Measures.tmdl", measures_tmdl())
    # reporte
    write(rep / ".platform", plat("Report"))
    write(rep / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    d = rep / "definition"
    write(d / "version.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
                               "version": "2.0.0"})
    theme = {"name": "72 HORAS (claro)", "dataColors": [BLUE, ORANGE, "#1BAF7A", "#EDA100", GREY],
             "foreground": INK, "background": BG, "tableAccent": BLUE}
    write(rep / "StaticResources" / "RegisteredResources" / "72H_theme.json", theme)
    rv = {"visual": "2.13.0", "report": "3.4.0", "page": "2.3.1"}
    report = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
              "themeCollection": {"customTheme": {"name": "72H_theme.json", "reportVersionAtImport": rv, "type": "RegisteredResources"}},
              "objects": {"section": [{"properties": {"verticalAlignment": L("'Top'")}}]},
              "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources",
                                    "items": [{"name": "72H_theme.json", "path": "72H_theme.json", "type": "CustomTheme"}]}],
              "settings": {"useStylableVisualContainerHeader": True, "exportDataMode": "AllowSummarized",
                           "defaultDrillFilterOtherVisuals": True, "allowChangeFilterTypes": True,
                           "useEnhancedTooltips": True, "useDefaultAggregateDisplayName": True, "locale": "es-MX"}}
    if base_theme and base_theme.exists():
        dest = rep / "StaticResources" / "SharedResources" / "BaseThemes" / base_theme.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(base_theme, dest)
        report["themeCollection"]["baseTheme"] = {"name": base_theme.stem, "reportVersionAtImport": rv, "type": "SharedResources"}
        report["resourcePackages"].insert(0, {"name": "SharedResources", "type": "SharedResources",
                                              "items": [{"name": base_theme.stem, "path": f"BaseThemes/{base_theme.name}", "type": "BaseTheme"}]})
    write(d / "report.json", report)
    order = []
    for i, (disp, visuals) in enumerate(pages(), 1):
        pid = f"p{i}" + uuid.uuid4().hex[:18]
        order.append(pid)
        write(d / "pages" / pid / "page.json",
              {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
               "name": pid, "displayName": disp, "displayOption": "FitToPage", "height": 720, "width": 1280,
               "objects": {"background": [{"properties": {"color": COLOR(BG), "transparency": L("0D")}}]}})
        for name, vjson in visuals:
            write(d / "pages" / pid / "visuals" / name / "visual.json", vjson)
    write(d / "pages" / "pages.json",
          {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
           "pageOrder": order, "activePageName": order[0]})
    write(OUT / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    return OUT


if __name__ == "__main__":
    bt = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    print(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_WIN_PATH, bt))
