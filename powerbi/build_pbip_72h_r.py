"""72 HORAS v0.2 — rediseño claro del tablero (PBIP), sobre el mismo modelo agregado.

Uso:  python powerbi/build_pbip_72h_r.py <ruta_windows_del_excel> <Fluent2.json> <09-Cdmx.geojson>
Salida: powerbi_rediseno/ (72HORAS_v02R.pbip + .Report + .SemanticModel + Excel del modelo).
Fondos de página: design_72h.py (se dibujan aquí y se registran como imágenes del informe).
"""
from __future__ import annotations
import json, shutil, sys, uuid
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_pbip_72h as base          # tablas, TMDL y medidas de la versión validada
import design_72h as D

ROOT = base.ROOT
OUT = ROOT / "powerbi_rediseno"
NAME = "72HORAS_v02R"
XLSX = "72H_PowerBI_model_v02R.xlsx"
L, COLOR, U = base.L, base.COLOR, base.U
NAVY, STEEL, STEEL_L, SLATE, SLATE_L, GRID, ORANGE, GREY_BAR, WHITE = (
    D.NAVY, D.STEEL, D.STEEL_L, D.SLATE, D.SLATE_L, D.GRID, D.ORANGE, D.GREY_BAR, D.WHITE)
FONTS = {"regular": "/usr/share/fonts/opentype/inter/Inter-Regular.otf",
         "semibold": "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"}
PAGE_IDS = {p: f"p{i + 1}{p}" for i, p in enumerate(D.PAGES)}
PAGE_NAMES = {"resumen": "Resumen", "sensibilidad": "Sensibilidad", "desenlace": "Desenlace",
              "caracteristicas": "Características", "alcaldia": "Alcaldía y calidad"}


# ---------------------------------------------------------------- datos
SIN_USO = {"Cifra publicada antes (E0)", "IC 95% superior", "Sexo · % ≤3 días", "Edad · % ≤3 días", "Año · % ≤3 días",
           "Fuente · % ≤3 días", "Alcaldía · % ≤3 días", "Anillo con vida", "Anillo sin vida",
           "IC y rango E3"}


def build_tables():
    t = base.build_tables()
    cs = t["cif_summary"]
    base.SORT_BY.update({"population_classes": {"clase": "orden", "clase_label": "orden"}})
    # (2) intervalos con la clasificación v0.2 (solo VALIDO; sin los 2 casos de orden imposible de la tabla v0.1)
    oi = pd.read_csv(base.T / "outcome_intervals_v02.csv", encoding="utf-8-sig").rename(
        columns={"CON VIDA": "con_vida", "SIN VIDA": "sin_vida", "DESCONOCIDA": "desconocida"})
    oi["orden"] = range(1, len(oi) + 1)
    pcv = pd.read_csv(base.T / "population_classes_v02.csv", encoding="utf-8-sig").set_index("clase").n
    assert int(oi.total.sum()) == int(pcv["VALIDO"]), "la tabla de intervalos debe sumar la clase VALIDO"
    t["outcome_intervals"] = oi[["intervalo", "orden", "con_vida", "sin_vida", "desconocida", "total", "pct_sin_vida_del_intervalo"]]
    acc = {"Alvaro Obregon": "Álvaro Obregón", "Benito Juarez": "Benito Juárez", "Coyoacan": "Coyoacán",
           "Cuauhtemoc": "Cuauhtémoc", "Tlahuac": "Tláhuac", "Sin Alcaldía Registrada": "Sin alcaldía registrada"}
    t["grp_alcaldia"]["valor"] = t["grp_alcaldia"]["valor"].replace(acc)
    pc = t["population_classes"]
    pc["clase_label"] = pc["clase"].map({"VALIDO": "Válido", "AMBIGUO": "Ambiguo", "SIN_FECHA": "Sin fecha",
                                         "IMPOSIBLE": "Imposible", "ABIERTO": "Abierto al corte"})
    for k in ("km_scenarios", "km_scenarios_3d"):  # E0 nunca se publicó formalmente: es la versión anterior del análisis
        t[k]["escenario_label"] = t[k]["escenario_label"].str.replace("versión publicada", "versión anterior", regex=False)
    for k in ("grp_sexo", "grp_edad", "grp_anio", "grp_fuente", "grp_alcaldia"):
        gdf = t[k]
        gdf["pct_r"] = gdf["pct_le3d_e3"].round(1)
        gdf["ic_txt"] = [f"{a:.1f}–{b:.1f}" for a, b in zip(gdf["ic_baja"], gdf["ic_alta"])]
        gdf["sf_r"] = gdf["pct_sin_fecha"].round(1)
        gdf["n_riesgo"] = gdf["n_riesgo"].astype("int64")
        base.SORT_BY.setdefault(k, {})["valor"] = "orden"
    c30 = cs[(cs.poblacion == "E3") & (cs.horizonte == 30)].set_index("desenlace").cif_pct
    loc30 = float(c30.sum())
    t["desenlace30"] = pd.DataFrame({"valor": ["Con vida", "Sin vida", "Desconocido", "Sin localización"],
                                     "orden": [1, 2, 3, 4],
                                     "pct": [float(c30["CON VIDA"]), float(c30["SIN VIDA"]), float(c30["DESCONOCIDA"]), round(100 - loc30, 2)]})
    base.SORT_BY["desenlace30"] = {"valor": "orden"}
    dq = t["data_quality"]
    dq["regla"] = dq["check"].map({
        "missing_report_date": "Sin fecha de reporte", "missing_event_date": "Sin fecha de desaparición",
        "missing_borough": "Sin alcaldía", "missing_location_date": "Sin fecha de localización",
        "location_before_report": "Localización antes del reporte", "location_before_event": "Localización antes de la desaparición",
        "report_before_event": "Reporte antes de la desaparición", "status_located_without_location_date": "Localizado sin fecha",
        "status_missing_with_location_date": "No localizado con fecha de localización", "duplicate_content": "Contenido duplicado",
        "historic_missing_date": "Fecha histórica atípica", "any_impossible_or_missing_core": "Imposible o sin dato clave"}).fillna(dq["check"])
    dq["categoria"] = dq["category"].map({"MISSING": "Faltante", "AMBIGUOUS": "Ambiguo", "IMPOSSIBLE": "Imposible",
                                          "MISMATCH": "Inconsistente", "DUPLICATE": "Duplicado", "OUTLIER": "Atípico",
                                          "DERIVED": "Derivada"}).fillna(dq["category"])
    return t


MEASURES_R = base.MEASURES + [
    ("% ≤3 días · E3", 'CALCULATE ( SUM ( km_scenarios_3d[pct] ), km_scenarios_3d[escenario] = "E3" ) / 100', "0.0%", "2 Series"),
    ("% ≤3 días · otros escenarios", 'CALCULATE ( SUM ( km_scenarios_3d[pct] ), km_scenarios_3d[escenario] <> "E3" ) / 100', "0.0%", "2 Series"),
    ("IC 95% banda", "( SUM ( km_curve_e3[ic_alta] ) - SUM ( km_curve_e3[ic_baja] ) ) / 100", "0.0%", "2 Series"),
    ("Marca 72 h", "IF ( MAX ( km_curve_e3[t] ) = 3, SUM ( km_curve_e3[pct_localizado] ) / 100 )", "0.0%", "2 Series"),
    ("Con vida ≤30 días (E3)", 'CALCULATE ( SUM ( cif_summary[cif_pct] ), cif_summary[poblacion] = "E3", cif_summary[desenlace] = "CON VIDA", cif_summary[horizonte] = 30 ) / 100', "0.0%", "1 Tarjetas"),
    ("Anillo con vida", "SUM ( ring_con_vida[valor] ) / 100", "0.0%", "2 Series"),
    ("Desconocido ≤30 días (E3)", 'CALCULATE ( SUM ( cif_summary[cif_pct] ), cif_summary[poblacion] = "E3", cif_summary[desenlace] = "DESCONOCIDA", cif_summary[horizonte] = 30 ) / 100', "0.0%", "1 Tarjetas"),
    ("Casos analizados (E3)", 'CALCULATE ( MAX ( km_scenarios_3d[n] ), km_scenarios_3d[escenario] = "E3" )', "#,0", "1 Tarjetas"),
    ("Desenlace a 30 días", "SUM ( desenlace30[pct] ) / 100", "0.0%", "2 Series"),
    ("Desconocido", "SUM ( cif_e3[desconocida] ) / 100", "0.0%", "2 Series"),
    ("Anillo sin vida", "SUM ( ring_sin_vida[valor] ) / 100", "0.0%", "2 Series"),
]


# ---------------------------------------------------------------- visuales
SCHEMA_V = base.SCHEMA_V
_z = iter(range(1, 100_000))


def _vc(vtype, x, y, w, h, alt, query=None, objects=None, vco_extra=None):
    n = next(_z)
    name = f"v{n:04d}{uuid.uuid4().hex[:12]}"
    vco = {"background": [{"properties": {"show": L("false")}}], "border": [{"properties": {"show": L("false")}}],
           "dropShadow": [{"properties": {"show": L("false")}}], "title": [{"properties": {"show": L("false")}}],
           "visualHeader": [{"properties": {"show": L("false")}}],
           "general": [{"properties": {"altText": L("'" + alt.replace("'", "''") + "'")}}]}
    vco.update(vco_extra or {})
    vis = {"visualType": vtype, **({"query": query} if query else {}), **({"objects": objects} if objects else {}),
           "visualContainerObjects": vco, "drillFilterOtherVisuals": True}
    return name, {"$schema": SCHEMA_V, "name": name,
                  "position": {"x": x, "y": y, "z": n * 100, "height": h, "width": w, "tabOrder": n * 100}, "visual": vis}


def run(t, size, color=NAVY, font="Segoe UI", bold=False):
    st = {"fontFamily": font, "fontSize": f"{size}pt", "color": color}
    if bold:
        st["fontWeight"] = "bold"
    return {"value": t, "textStyle": st}


def text(x, y, w, h, paras, alt="Texto", align=None):
    ps = []
    for p in paras:
        p = p if isinstance(p, list) else [p]
        d = {"textRuns": p}
        if align:
            d["horizontalTextAlignment"] = align
        ps.append(d)
    return _vc("textbox", x, y, w, h, alt, objects={"general": [{"properties": {"paragraphs": ps}}]})


def _m(n, disp=None):
    return {"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": n}},
            "queryRef": f"_Measures.{n}", "nativeQueryRef": disp or n, "displayName": disp or n}


def _c(t, c, disp=None):
    return {"field": {"Column": {"Expression": {"SourceRef": {"Entity": t}}, "Property": c}},
            "queryRef": f"{t}.{c}", "nativeQueryRef": disp or c, "displayName": disp or c, "active": True}


def _w(s, pt, light=True):
    """Ancho aproximado (px) de una cifra en Segoe UI para ceñir tarjetas centradas."""
    em = pt * 96 / 72
    k = {",": .28, ".": .28, "%": .82, "–": .5, " ": .27}
    return int(sum(k.get(ch, .56 if light else .58) for ch in s) * em) + 18


def kpi(x, y, measure, sample, pt, color=NAVY, font="Segoe UI Light", h=None, w=None):
    w = w or _w(sample, pt)
    obj = {"labels": [{"properties": {"color": COLOR(color), "fontSize": L(f"{pt}D"), "fontFamily": L(f"'{font}'")}}],
           "categoryLabels": [{"properties": {"show": L("false")}}]}
    return _vc("card", x, y, w, h or int(pt * 2.1), f"Indicador: {measure}",
               {"queryState": {"Values": {"projections": [_m(measure)]}}}, obj)


def _axis(show=True, color=SLATE, size=9, grid=False):
    p = {"show": L("true" if show else "false"), "labelColor": COLOR(color), "fontSize": L(f"{size}D"),
         "fontFamily": L("'Segoe UI'"), "showAxisTitle": L("false"), "gridlineShow": L("true" if grid else "false")}
    if grid:
        p.update({"gridlineColor": COLOR(GRID), "gridlineStyle": L("'dotted'"), "gridlineThickness": L("1D")})
    return p


def chart(vtype, x, y, w, h, table, cat, measures, colors, alt, *, labels=False, value_axis=False, grid=False,
          scalar=False, y_range=None, strokes=None, markers=(), label_series=None, axis_label_color=SLATE,
          sort_asc=True, cat_size=9, label_colors=None, label_pos=None):
    q = {"queryState": {"Category": {"projections": [_c(table, cat)]},
                        "Y": {"projections": [_m(m, d) for m, d in measures]}}}
    if sort_asc:
        q["sortDefinition"] = {"sort": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": cat}},
                                         "direction": "Ascending"}], "isDefaultSort": True}
    cax = _axis(True, axis_label_color, cat_size)
    if scalar:
        cax["axisType"] = L("'Scalar'")
    vax = _axis(value_axis, axis_label_color if value_axis else SLATE_L, 8, grid)
    if y_range:
        vax["start"], vax["end"] = L(f"{y_range[0]}D"), L(f"{y_range[1]}D")
    obj = {"legend": [{"properties": {"show": L("false")}}], "categoryAxis": [{"properties": cax}],
           "valueAxis": [{"properties": vax}],
           "dataPoint": [{"properties": {"fill": COLOR(c)}, "selector": {"metadata": f"_Measures.{m}"}}
                         for (m, _), c in zip(measures, colors)],
           "labels": [{"properties": {"show": L("true" if labels else "false"), "color": COLOR(NAVY),
                                      "fontSize": L("9D"), "fontFamily": L("'Segoe UI Semibold'")}}]}
    if label_pos:
        obj["labels"][0]["properties"]["labelPosition"] = L(f"'{label_pos}'")
    for m, c in (label_colors or {}).items():
        obj["labels"].append({"properties": {"color": COLOR(c)}, "selector": {"metadata": f"_Measures.{m}"}})
    if label_series is not None:  # etiquetas solo en una serie
        obj["labels"][0]["properties"]["show"] = L("true")
        for m, _ in measures:
            obj["labels"].append({"properties": {"showSeries": L("true" if m == label_series else "false")},
                                  "selector": {"metadata": f"_Measures.{m}"}})
    if strokes:
        obj["lineStyles"] = [{"properties": {"strokeWidth": L(f"{sw}L"), "showMarker": L("true" if m in markers else "false"),
                                             **({"markerSize": L("7D"), "markerColor": COLOR(NAVY)} if m in markers else {})},
                              "selector": {"metadata": f"_Measures.{m}"}} for (m, _), sw in zip(measures, strokes)]
    if vtype in ("clusteredBarChart", "columnChart", "clusteredColumnChart"):
        obj["layout"] = [{"properties": {"ribbonGapSize": L("0L")}}]
    return _vc(vtype, x, y, w, h, alt, q, obj)


def donut(x, y, w, h, table, cat, measure, main, color, alt):
    q = {"queryState": {"Category": {"projections": [_c(table, cat)]}, "Y": {"projections": [_m(measure)]}}}
    sel = lambda v: {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0,
                                                          "Left": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": cat}},
                                                          "Right": {"Literal": {"Value": f"'{v}'"}}}}}]}
    obj = {"legend": [{"properties": {"show": L("false")}}], "labels": [{"properties": {"show": L("false")}}],
           "slices": [{"properties": {"innerRadiusRatio": L("74L")}}],
           "dataPoint": [{"properties": {"fill": COLOR(color)}, "selector": sel(main)},
                         {"properties": {"fill": COLOR("#E6EBF1")}, "selector": sel("Resto")}]}
    return _vc("donutChart", x, y, w, h, alt, q, obj)


def table(x, y, w, h, tname, cols, alt, size=9, pad=2):
    q = {"queryState": {"Values": {"projections": [_c(tname, c, d) for c, d in cols]}}}
    obj = {"grid": [{"properties": {"gridVertical": L("false"), "gridHorizontal": L("true"),
                                    "gridHorizontalColor": COLOR(GRID), "rowPadding": L(f"{pad}D"), "textSize": L(f"{size}D"),
                                    "outlineColor": COLOR(GRID)}}],
           "columnHeaders": [{"properties": {"fontColor": COLOR(SLATE), "backColor": COLOR(WHITE), "fontSize": L(f"{size}D"),
                                             "fontFamily": L("'Segoe UI Semibold'"), "outline": L("'BottomOnly'")}}],
           "values": [{"properties": {"fontColorPrimary": COLOR(NAVY), "backColorPrimary": COLOR(WHITE),
                                      "fontColorSecondary": COLOR(NAVY), "backColorSecondary": COLOR("#F6F8FA"),
                                      "fontSize": L(f"{size}D"), "fontFamily": L("'Segoe UI'")}}]}
    return _vc("tableEx", x, y, w, h, alt, q, obj)


def nav_button(i, target):
    cy = D.NAV_Y0 + i * D.NAV_STEP
    obj = {"icon": [{"properties": {"shapeType": L("'blank'")}, "selector": {"id": "default"}}],
           "fill": [{"properties": {"show": L("true"), "fillColor": COLOR(WHITE), "transparency": L("100D")}, "selector": {"id": "default"}}],
           "outline": [{"properties": {"show": L("false")}, "selector": {"id": "default"}}],
           "text": [{"properties": {"show": L("false")}, "selector": {"id": "default"}}]}
    vco = {"visualLink": [{"properties": {"show": L("true"), "type": L("'PageNavigation'"),
                                          "navigationSection": L(f"'{PAGE_IDS[target]}'")}}]}
    name, v = _vc("actionButton", 14, cy - 22, 44, 44, f"Ir a {PAGE_NAMES[target]}", None, obj, vco)
    v["visual"]["visualContainerObjects"]["title"] = [{"properties": {"show": L("false"), "text": L(f"'{PAGE_NAMES[target]}'")}}]
    v["howCreated"] = "InsertVisualButton"
    return name, v


def card_title(box, title, sub=None):
    x, y, w, h = box
    out = [text(x + 10, y + 10, w - 20, 26, [run(title, 11, NAVY, "Segoe UI Semibold")], "Título de tarjeta")]
    if sub:
        out.append(text(x + 10, y + 32, w - 20, 22, [sub if isinstance(sub, list) else run(sub, 8.5, SLATE)], "Subtítulo de tarjeta"))
    return out


# ---------------------------------------------------------------- páginas
FECHA_NOTA = ("Fecha de localización registrada: no es fecha de fallecimiento y la fuente no documenta "
              "a qué momento del proceso corresponde.")
NOTE = ("La fuente no contiene horas: se utiliza ≤3 días calendario como aproximación operativa de las primeras 72 horas. "
        "72 horas es un hito de medición, no un plazo de espera: la búsqueda es inmediata.")


def chrome(page, title, subtitle):
    v = [text(16, 25, 40, 30, [run("72", 13, WHITE, "Segoe UI", True)], "Marca 72 HORAS", "center")]
    v += [nav_button(i, p) for i, p in enumerate(D.PAGES)]
    v.append(text(90, 8, 900, 44, [run(title, 17, NAVY, "Segoe UI Semibold")], "Título de página"))
    v.append(text(90, 46, 900, 28, [run(subtitle, 9.5, SLATE)], "Subtítulo de página"))
    v.append(text(990, 16, 272, 46, [run("72 HORAS · CBPCDMX, Registro Interno", 8.5, NAVY, "Segoe UI Semibold"),
                                     run("Reportes 25-jun-2019 a 14-nov-2022 · corte 15-nov-2022", 8, SLATE)],
                  "Fuente", "right"))
    v.append(text(90, 696, 1170, 22, [run(NOTE, 7.5, SLATE_L)], "Nota"))
    return v


def bars_by_cat(x, y, w, h, table, cat, measure, colors, alt, cat_size=9, vtype="clusteredBarChart", label_pos=None):
    """Barras (o columnas) con un color por categoría (selector por valor de la categoría)."""
    name, v = chart(vtype, x, y, w, h, table, cat, [(measure, measure)], [STEEL], alt, labels=True, cat_size=cat_size,
                    label_pos=label_pos)
    sel = lambda val: {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0,
                                                            "Left": {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": cat}},
                                                            "Right": {"Literal": {"Value": f"'{val}'"}}}}}]}
    v["visual"]["objects"]["dataPoint"] = [{"properties": {"fill": COLOR(c)}, "selector": sel(val)} for val, c in colors.items()]
    return name, v


def slicer(x, y, w, h, tname, col, disp, alt):
    """Segmentador desplegable (selección múltiple; sin selección = todos)."""
    q = {"queryState": {"Values": {"projections": [_c(tname, col, disp)]}}}
    obj = {"data": [{"properties": {"mode": L("'Dropdown'")}}],
           "selection": [{"properties": {"singleSelect": L("false"), "selectAllCheckboxEnabled": L("false")}}],
           "header": [{"properties": {"show": L("true"), "fontColor": COLOR(SLATE), "textSize": L("8D")}}],
           "items": [{"properties": {"fontColor": COLOR(NAVY), "background": COLOR("#EEF2F6"), "textSize": L("9D")}}]}
    return _vc("slicer", x, y, w, h, alt, q, obj, {"subTitle": [{"properties": {"show": L("false")}}]})


def group_table(x, y, w, h, tname, first, alt, size=10, pad=4):
    """Tabla de grupo con estimación, IC 95%, n y % de localizados sin fecha (alineación numérica a la derecha)."""
    name, v = table(x, y, w, h, tname, [("valor", first), ("pct_r", "% ≤3 días"), ("ic_txt", "IC 95%"),
                                        ("n_riesgo", "n"), ("sf_r", "% sin fecha")], alt, size, pad)
    v["visual"]["objects"]["columnFormatting"] = [
        {"properties": {"alignment": L("'Right'")}, "selector": {"metadata": f"{tname}.{c}"}} for c in ("pct_r", "ic_txt", "n_riesgo", "sf_r")]
    v["visual"]["objects"]["values"].append({"properties": {"fontColorPrimary": COLOR(STEEL), "fontColorSecondary": COLOR(STEEL),
                                                            "fontFamily": L("'Segoe UI Semibold'")},
                                             "selector": {"metadata": f"{tname}.pct_r"}})
    return name, v


def pages(tb):
    P, LY = [], D.LAYOUT
    sc3 = tb["km_scenarios_3d"].set_index("escenario")
    e3, e0, e2b, e2a = sc3.loc["E3"], sc3.loc["E0"], sc3.loc["E2-baja"], sc3.loc["E2-alta"]
    r1 = lambda v: str(Decimal(str(round(float(v), 6))).quantize(Decimal("0.1"), ROUND_HALF_UP))
    pct = lambda v: f"{r1(v)}%"
    cs = tb["cif_summary"]
    c30 = lambda dsl: float(cs[(cs.poblacion == "E3") & (cs.desenlace == dsl) & (cs.horizonte == 30)].cif_pct.iloc[0])
    cv30, sv30, dk30 = c30("CON VIDA"), c30("SIN VIDA"), c30("DESCONOCIDA")
    loc30 = cv30 + sv30 + dk30
    pc = tb["population_classes"].set_index("clase").n
    n_total, n_e3, n_imp, n_open, n_sf = int(pc.sum()), int(e3.n), int(pc["IMPOSIBLE"]), int(pc["ABIERTO"]), int(pc["SIN_FECHA"])
    ic3 = f"{r1(e3.ic_baja)}–{r1(e3.ic_alta)}%"
    rango = f"{r1(e2b.pct)}–{r1(e2a.pct)}%"
    assert n_total - n_imp == n_e3
    n_amb = int(pc["AMBIGUO"])

    # 1 · Resumen ---------------------------------------------------------------------------------
    R = LY["resumen"]
    v = chrome("resumen", f"Se estima que {pct(e3.pct)} de los casos tiene localización documentada en ≤3 días",
               f"Estimación principal E3 sobre {n_e3:,} casos analizados ({n_total:,} registros recibidos). "
               "Personas reportadas como desaparecidas en la CDMX.")
    x, y, w, h = R["A"]
    v += [text(x + 10, y + 12, w - 20, 22, [run("Registros recibidos", 10, SLATE, "Segoe UI Semibold")], "Etiqueta", "center"),
          kpi(x + 10, y + 34, "Casos recibidos", f"{n_total:,}", 36, h=76, w=w - 20),
          text(x + 10, y + 108, w - 20, 36, [run(f"Reportes del 25-jun-2019 al 14-nov-2022 · {n_imp} con fechas imposibles "
                                                 "quedan fuera de la estimación", 8, SLATE)], "Nota", "center")]
    x, y, w, h = R["B"]
    for i, (lab, meas, sample, sub) in enumerate((
            ("Analizados en E3", "Casos analizados (E3)", f"{n_e3:,}", f"{r1(n_e3 / n_total * 100)}% de los registros"),
            ("Abiertos al corte", "Abiertos al corte", f"{n_open:,}", f"{r1(n_open / n_total * 100)}% de los registros"))):
        cx0 = x + 8 + i * 160
        v += [text(cx0, y + 54, 144, 22, [run(lab, 8.5, SLATE)], "Etiqueta", "center"),
              kpi(cx0, y + 70, meas, sample, 18, NAVY, "Segoe UI Semibold", 56, 144),
              text(cx0, y + 126, 144, 22, [run(sub, 8, SLATE_L)], "Detalle", "center")]
    box = R["C"]
    v += card_title(box, "Curva de localización documentada", "% acumulado por días desde el reporte (E3) · banda: IC 95%")
    x, y, w, h = box
    cbox = (x + 6, y + 58, w - 12, h - 64)
    v.append(chart("stackedAreaChart", *cbox, "km_curve_e3", "t", [("IC 95% inferior", "IC inf."), ("IC 95% banda", "Banda")],
                   [WHITE, STEEL_L], "Banda IC 95%", scalar=True, value_axis=True, y_range=(0, 0.6),
                   axis_label_color=WHITE, sort_asc=True, cat_size=8))
    v.append(chart("lineChart", *cbox, "km_curve_e3", "t", [("Localización acumulada (E3)", "E3"), ("Marca 72 h", "72 h")],
                   [STEEL, NAVY], "Curva E3 con marca a 72 horas", scalar=True, value_axis=True, grid=True,
                   y_range=(0, 0.6), strokes=[3, 1], markers=("Marca 72 h",), label_series="Marca 72 h", cat_size=8))
    # panel central: el hallazgo de sensibilidad
    box = R["M"]
    v += card_title(box, "¿Cuánto cambia la cifra según cómo se tratan los datos?",
                    [run("■ ", 9, STEEL), run("E3 · estimación principal    ", 8.5, SLATE), run("■ ", 9, GREY_BAR),
                     run("otros tratamientos de los mismos registros", 8.5, SLATE)])
    x, y, w, h = box
    v.append(bars_by_cat(x + 8, y + 62, w - 16, h - 62 - 150, "km_scenarios_3d", "escenario_label", "% ≤3 días por escenario",
                        {lb: (STEEL if es == "E3" else GREY_BAR) for es, lb in zip(tb["km_scenarios_3d"].escenario,
                                                                                    tb["km_scenarios_3d"].escenario_label)},
                        "Columnas por escenario", cat_size=8, vtype="clusteredColumnChart", label_pos="OutsideEnd"))
    v.append(text(x + 14, y + h - 142, w - 28, 132, [
        [run(f"De {pct(e0.pct)} a {pct(e2a.pct)} ", 11, NAVY, "Segoe UI Semibold"),
         run("con los mismos registros: la cifra depende de cómo se tratan los casos incompletos.", 9, SLATE)],
        [run("Rango de sensibilidad ", 8.5, NAVY, "Segoe UI Semibold"), run(rango, 8.5, STEEL, "Segoe UI Semibold"),
         run(f" · cambia según cómo se traten {n_sf} localizados sin fecha (E2-baja a E2-alta).", 8.5, SLATE)],
        [run("IC 95% de E3 ", 8.5, NAVY, "Segoe UI Semibold"), run(ic3, 8.5, STEEL, "Segoe UI Semibold"),
         run(" · incertidumbre estadística de la estimación principal. No son la misma medida.", 8.5, SLATE)]],
        "Lectura de sensibilidad"))
    # estimación principal y su incertidumbre
    x, y, w, h = R["D"]
    v += [text(x + 10, y + 12, w - 20, 22, [run("Estimación principal ≤3 días (E3)", 10, SLATE, "Segoe UI Semibold")], "Etiqueta", "center"),
          kpi(x + 10, y + 34, "% localizado ≤3 días (E3)", pct(e3.pct), 36, h=76, w=w - 20),
          text(x + 14, y + 118, w - 28, 204, [
              [run("IC 95%  ", 9, NAVY, "Segoe UI Semibold"), run(ic3, 9, STEEL, "Segoe UI Semibold")],
              run("Incertidumbre estadística (bootstrap, B = 1,000).", 8, SLATE),
              run(" ", 4, SLATE),
              [run("Rango de sensibilidad  ", 9, NAVY, "Segoe UI Semibold"), run(rango, 9, STEEL, "Segoe UI Semibold")],
              run(f"Según cómo se traten {n_sf} localizados sin fecha.", 8, SLATE),
              run(" ", 4, SLATE),
              [run("Versión anterior del análisis  ", 9, NAVY, "Segoe UI Semibold"), run(pct(e0.pct), 9, SLATE, "Segoe UI Semibold")],
              run(f"Dejaba fuera {n_amb + n_sf} localizados que E3 sí incluye.", 8, SLATE),
              run(" ", 4, SLATE),
              [run("Incluye localizaciones previas  ", 9, NAVY, "Segoe UI Semibold"), run(f"{n_amb} casos", 9, SLATE, "Segoe UI Semibold")],
              run("Localizados antes de que se registrara el reporte; se cuentan como día 0.", 8, SLATE)], "Incertidumbre")]
    # desenlace a 30 días (lee el modelo; nada dibujado en el fondo)
    box = R["E"]
    v += card_title(box, "Desenlace a 30 días del reporte", f"E3 · {pct(loc30)} con localización documentada")
    x, y, w, h = box
    v.append(bars_by_cat(x + 6, y + 58, w - 12, h - 122, "desenlace30", "valor", "Desenlace a 30 días",
                         {"Con vida": STEEL, "Sin vida": ORANGE, "Desconocido": SLATE, "Sin localización": GREY_BAR},
                         "Barras: desenlace a 30 días", cat_size=8))
    v.append(text(x + 10, y + h - 62, w - 20, 56, [run(FECHA_NOTA, 7.5, SLATE_L)], "Nota"))
    P.append(("resumen", v))

    # 2 · Sensibilidad -----------------------------------------------------------------------------
    S2 = LY["sensibilidad"]
    v = chrome("sensibilidad", f"La estimación cambia de {pct(e0.pct)} a {pct(e3.pct)} al modificar el tratamiento de los registros",
               f"¿Qué tan confiables son los indicadores de localización? Con los mismos registros, la cifra va de {pct(e0.pct)} "
               f"a {pct(e2a.pct)} según cómo se traten los datos incompletos.")
    v += card_title(S2["L"], "% con localización documentada ≤3 días, por escenario",
                    [run("■ ", 9, STEEL), run("E3 · estimación principal    ", 8.5, SLATE), run("■ ", 9, GREY_BAR),
                     run("otros escenarios", 8.5, SLATE)])
    x, y, w, h = S2["L"]
    v.append(chart("columnChart", x + 8, y + 64, w - 16, h - 64 - 84, "km_scenarios_3d", "escenario_label",
                   [("% ≤3 días · E3", "E3"), ("% ≤3 días · otros escenarios", "Otros")], [STEEL, GREY_BAR],
                   "Columnas por escenario", labels=True, cat_size=9, label_pos="InsideEnd",
                   label_colors={"% ≤3 días · E3": WHITE}))
    v.append(text(x + 14, y + h - 80, w - 28, 72, [
        [run("Rango de sensibilidad ", 9, NAVY, "Segoe UI Semibold"), run(rango, 9, STEEL, "Segoe UI Semibold"),
         run(f" (E2-baja a E2-alta): refleja la decisión sobre {n_sf} localizados sin fecha.", 9, SLATE)],
        [run("IC 95% de E3 ", 9, NAVY, "Segoe UI Semibold"), run(ic3, 9, STEEL, "Segoe UI Semibold"),
         run(": incertidumbre estadística de la estimación principal. Son medidas distintas.", 9, SLATE)]],
        "Rango frente a IC"))
    v += card_title(S2["R"], "Todos los horizontes", "% localizado e IC 95% bootstrap (B = 1,000)")
    x, y, w, h = S2["R"]
    v.append(slicer(x + 10, y + 58, 272, 50, "km_scenarios", "escenario", "Escenario", "Segmentador de escenario"))
    v.append(slicer(x + 292, y + 58, w - 302, 50, "km_scenarios", "horizonte", "Días", "Segmentador de días"))
    v.append(table(x + 10, y + 112, w - 20, h - 122, "km_scenarios",
                   [("escenario", "Escenario"), ("horizonte", "Días"), ("pct", "%"), ("ic_baja", "IC inf."),
                    ("ic_alta", "IC sup."), ("n", "n")], "Tabla de escenarios", 9))
    P.append(("sensibilidad", v))

    # 3 · Desenlace -------------------------------------------------------------------------------
    S3 = LY["desenlace"]
    v = chrome("desenlace", f"A 30 días, {pct(loc30)} tiene localización documentada; {pct(sv30)} se localizó sin vida",
               "Aalen-Johansen exacto, población E3. Fecha de localización registrada: no es fecha de fallecimiento ni se sabe "
               "a qué momento del proceso corresponde.")
    v += card_title(S3["L"], "Incidencia acumulada por desenlace, 0–30 días",
                    [run("━ ", 9, STEEL, "Segoe UI", True), run("con vida    ", 8.5, SLATE),
                     run("━ ", 9, ORANGE, "Segoe UI", True), run("sin vida    ", 8.5, SLATE),
                     run("━ ", 9, SLATE, "Segoe UI", True), run("desconocido", 8.5, SLATE)])
    x, y, w, h = S3["L"]
    v.append(chart("lineChart", x + 8, y + 64, w - 16, h - 72, "cif_e3", "t",
                   [("Con vida", "Con vida"), ("Sin vida", "Sin vida"), ("Desconocido", "Desconocido")],
                   [STEEL, ORANGE, SLATE], "Líneas por desenlace", scalar=True, value_axis=True, grid=True,
                   y_range=(0, 0.6), strokes=[3, 3, 2]))
    x, y, w, h = S3["RT"]
    v.append(text(x + 10, y + 10, w - 20, 26, [run("A 30 días del reporte", 11, NAVY, "Segoe UI Semibold")], "Título"))
    cw = (w - 24) // 3
    for i, (lab, meas, col, sample) in enumerate((("Con vida", "Con vida ≤30 días (E3)", STEEL, pct(cv30)),
                                                   ("Sin vida", "Sin vida ≤30 días (E3)", ORANGE, pct(sv30)),
                                                   ("Desconocido", "Desconocido ≤30 días (E3)", SLATE, pct(dk30)))):
        dx = x + 12 + i * cw
        v += [text(dx, y + 50, cw, 22, [run(lab, 9, SLATE)], "Etiqueta", "center"),
              kpi(dx, y + 72, meas, sample, 26, col, "Segoe UI Light", 64, cw)]
    v.append(text(x + 10, y + 150, w - 20, 76, [run(f"Suman {pct(loc30)} con localización documentada a 30 días (E3). "
                                                    f"El {pct(100 - loc30)} restante no tenía localización documentada a 30 días.",
                                                    8, SLATE_L)], "Nota"))
    v += card_title(S3["RB"], "Localizados con fecha válida, por intervalo", "Casos por desenlace y % sin vida dentro de cada intervalo")
    x, y, w, h = S3["RB"]
    v.append(table(x + 10, y + 62, w - 20, h - 72, "outcome_intervals",
                   [("intervalo", "Intervalo"), ("con_vida", "Con vida"), ("sin_vida", "Sin vida"),
                    ("desconocida", "Desconocido"), ("pct_sin_vida_del_intervalo", "% sin vida")], "Tabla por intervalo", 9))
    P.append(("desenlace", v))

    # 4 · Características -------------------------------------------------------------------------
    S4 = LY["caracteristicas"]
    v = chrome("caracteristicas", "Características asociadas con la localización en ≤3 días · asociación, no causa",
               f"E3 por grupo con IC 95%, n y % sin fecha. General {pct(e3.pct)} (IC {ic3}). IC sin traslape = diferencia; "
               "con traslape, la comparación visual no basta.")
    gk = pd.read_csv(base.T / "group_kpis_v02.csv", encoding="utf-8-sig")
    oculto = gk[gk.below_min_sample_size == 1].groupby("grupo").n_riesgo.sum()
    for k, (tname, ttl, first, gname) in zip("ABCD", (("grp_sexo", "Sexo", "Sexo", "sex"), ("grp_edad", "Grupo de edad", "Edad", "age_group"),
                                                      ("grp_anio", "Año de reporte", "Año", "report_year"),
                                                      ("grp_fuente", "Fuente del reporte", "Fuente", "report_source"))):
        sub = "Solo grupos con ≥30 localizaciones observadas"
        if int(oculto.get(gname, 0)):  # se explica el total cuando un grupo «sin dato» queda oculto
            sub += f" · no se muestra «sin dato» ({int(oculto[gname])} casos) · total E3: {n_e3:,}"
        v += card_title(S4[k], ttl, sub)
        x, y, w, h = S4[k]
        v.append(group_table(x + 10, y + 50, w - 20, h - 56, tname, first, f"Tabla: {ttl}", 11, 3))
    P.append(("caracteristicas", v))

    # 5 · Alcaldía y calidad -----------------------------------------------------------------------
    S5 = LY["alcaldia"]
    ga = tb["grp_alcaldia"]
    sd = ga[ga.valor == "Sin alcaldía registrada"].iloc[0]
    reales = ga[ga.valor != "Sin alcaldía registrada"]
    n_alc = len(reales)
    assert reales.ic_baja.max() < reales.ic_alta.min(), "las alcaldías mostradas ya no se traslapan todas"
    assert sd.ic_alta < reales.ic_baja.min(), "«sin alcaldía» ya se traslapa con alguna alcaldía"
    alc_ocultas = gk[(gk.grupo == "borough_missing") & (gk.below_min_sample_size == 1)]
    v = chrome("alcaldia", "Alcaldía de la desaparición y calidad del registro",
               f"Los IC 95% de las {n_alc} alcaldías mostradas se traslapan: no se presenta ranking (orden alfabético). "
               "Más reportes no implica mayor peligrosidad.")
    v += card_title(S5["L"], "% con localización documentada ≤3 días, por alcaldía",
                    "E3 · alcaldías con ≥30 localizaciones · compare los IC antes de comparar alcaldías")
    x, y, w, h = S5["L"]
    v.append(group_table(x + 10, y + 62, w - 20, 452, "grp_alcaldia", "Alcaldía", "Tabla por alcaldía", 11, 3))
    v.append(text(x + 10, y + 518, w - 20, 80, [
        [run("Sin alcaldía registrada  ", 9, NAVY, "Segoe UI Semibold"),
         run(f"{r1(sd.pct_le3d_e3)}% (IC {r1(sd.ic_baja)}–{r1(sd.ic_alta)}%)", 9, STEEL, "Segoe UI Semibold")],
        run("No se traslapa con ninguna alcaldía: diferencia descriptiva que requiere investigación adicional.", 8.5, SLATE),
        run(f"Se omiten {len(alc_ocultas)} grupos con menos de 30 localizaciones ({int(alc_ocultas.n_riesgo.sum())} casos): "
            "Cuajimalpa, Magdalena Contreras, Otro, Milpa Alta y Naucalpan.", 8.5, SLATE)], "Nota sobre alcaldías"))
    v += card_title(S5["RT"], f"Clases de población ({n_total:,} registros)", "Qué entra en cada estimación")
    x, y, w, h = S5["RT"]
    v.append(chart("clusteredBarChart", x + 8, y + 60, w - 16, h - 66, "population_classes", "clase_label",
                   [("Casos por clase", "Casos")], [SLATE], "Barras por clase", labels=True, cat_size=9))
    v += card_title(S5["RB"], "Reglas de calidad del registro",
                    "Casos afectados por regla. Un caso puede incumplir varias reglas: los conteos se superponen y no se suman.")
    x, y, w, h = S5["RB"]
    v.append(table(x + 10, y + 62, w - 20, 244, "data_quality",
                   [("regla", "Regla"), ("categoria", "Categoría"), ("affected_rows", "Casos"), ("pct_rows", "%")],
                   "Tabla de calidad", 8.5, 0))
    dqi = tb["data_quality"].set_index("regla").affected_rows
    n_sfl = int(dqi["Sin fecha de localización"])
    assert n_sfl == n_open + n_sf, "sin fecha de localización ya no es abiertos + localizados sin fecha"
    v.append(text(x + 10, y + 310, w - 20, 44, [[
        run(f"Sin fecha de localización ({n_sfl:,})", 8.5, NAVY, "Segoe UI Semibold"),
        run(f" = {n_open:,} casos abiertos al corte, que aún no tienen localización (falta legítima), + {n_sf} localizados "
            "sin fecha: información incompleta que requiere revisión.", 8.5, SLATE)]], "Nota sobre fechas faltantes"))
    P.append(("alcaldia", v))
    return P


# ---------------------------------------------------------------- escritura
def theme():
    return {"name": "72 HORAS (claro)", "dataColors": [STEEL, ORANGE, SLATE, GREY_BAR, NAVY, STEEL_L],
            "foreground": NAVY, "foregroundNeutralSecondary": SLATE, "background": WHITE, "tableAccent": STEEL,
            "textClasses": {"callout": {"fontSize": 28, "fontFace": "Segoe UI Light", "color": NAVY},
                            "title": {"fontSize": 11, "fontFace": "Segoe UI Semibold", "color": NAVY},
                            "header": {"fontSize": 10, "fontFace": "Segoe UI Semibold", "color": NAVY},
                            "label": {"fontSize": 9, "fontFace": "Segoe UI", "color": SLATE}},
            "visualStyles": {"*": {"*": {"background": [{"show": False}], "border": [{"show": False}],
                                         "dropShadow": [{"show": False}]}}}}


def main(win_xlsx, base_theme: Path, geojson: Path):
    write = base.write
    OUT.mkdir(exist_ok=True)
    tables = build_tables()
    with pd.ExcelWriter(OUT / XLSX) as xw:
        for n, df in tables.items():
            df.to_excel(xw, sheet_name=n, index=False)
    rep, sm = OUT / f"{NAME}.Report", OUT / f"{NAME}.SemanticModel"
    for d_ in (rep, sm):
        if d_.exists():
            shutil.rmtree(d_)
    write(OUT / f"{NAME}.pbip", {"version": "1.0", "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
                                 "settings": {"enableAutoRecovery": True}})
    plat = lambda t: {"$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
                      "metadata": {"type": t, "displayName": NAME}, "config": {"version": "2.0", "logicalId": U()}}
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
        tm = base.table_tmdl(n, df)
        for col in ("pct_r", "sf_r"):
            tm = tm.replace(f"\tcolumn {col}\n\t\tdataType: double\n\t\tformatString: 0.00", f"\tcolumn {col}\n\t\tdataType: double\n\t\tformatString: 0.0")
        write(sm / "definition" / "tables" / f"{n}.tmdl", tm)
    base.MEASURES[:] = [m for m in MEASURES_R if m[0] not in SIN_USO]
    write(sm / "definition" / "tables" / "_Measures.tmdl", base.measures_tmdl())
    # informe
    write(rep / ".platform", plat("Report"))
    write(rep / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}}})
    d = rep / "definition"
    write(d / "version.json", {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
                               "version": "2.0.0"})
    res = rep / "StaticResources" / "RegisteredResources"
    write(res / "72H_theme_claro.json", theme())
    cases = pd.read_csv(ROOT / "dashboard" / "data_v02" / "fact_cases_LOCAL_v02.csv", encoding="utf-8-sig")["borough_missing"].value_counts().to_dict()
    D.RINGS[:] = []
    bgs = D.render_all(res, geojson, cases, FONTS)
    rv = {"visual": "2.13.0", "report": "3.4.0", "page": "2.3.1"}
    items = [{"name": "72H_theme_claro.json", "path": "72H_theme_claro.json", "type": "CustomTheme"}] + \
            [{"name": f.name, "path": f.name, "type": "Image"} for f in bgs]
    report = {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
              "themeCollection": {"customTheme": {"name": "72H_theme_claro.json", "reportVersionAtImport": rv, "type": "RegisteredResources"}},
              "objects": {"section": [{"properties": {"verticalAlignment": L("'Top'")}}]},
              "resourcePackages": [{"name": "RegisteredResources", "type": "RegisteredResources", "items": items}],
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
    for key, visuals in pages(tables):
        pid = PAGE_IDS[key]
        order.append(pid)
        img = f"bg_{key}.png"
        bg = {"color": COLOR(D.CANVAS_BOT), "transparency": L("0D"),
              "image": {"image": {"name": L(f"'{img}'"),
                                  "url": {"expr": {"ResourcePackageItem": {"PackageName": "RegisteredResources", "PackageType": 1, "ItemName": img}}},
                                  "scaling": L("'Fit'")}}}
        write(d / "pages" / pid / "page.json",
              {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
               "name": pid, "displayName": PAGE_NAMES[key], "displayOption": "FitToPage", "height": 720, "width": 1280,
               "objects": {"background": [{"properties": bg}],
                           "outspace": [{"properties": {"color": COLOR(D.CANVAS_BOT)}}]}})
        for name, vjson in visuals:
            write(d / "pages" / pid / "visuals" / name / "visual.json", vjson)
    write(d / "pages" / "pages.json",
          {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
           "pageOrder": order, "activePageName": order[0]})
    write(OUT / ".gitignore", "**/.pbi/localSettings.json\n**/.pbi/cache.abf\n")
    return OUT


if __name__ == "__main__":
    print(main(sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])))
