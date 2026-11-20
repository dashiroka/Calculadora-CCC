"""Aplicación web del ejercicio 8.4 — Cosmic Computer Company."""
import io
import json

import numpy as np
import pandas as pd
import streamlit as st

from solver_ccc import DATOS_ORIGINALES, resolver, moneda

st.set_page_config(page_title="Calculadora CCC | Optimización", page_icon="🏭", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
    .block-container {padding-top: 2rem; max-width: 1280px;}
    .main-title {font-size:2.5rem; font-weight:800; margin-bottom:.1rem; color:var(--text-color, #742d23)}
    .eyebrow {font-size:.85rem; letter-spacing:.17em; font-weight:700; color:var(--text-color, #742d23)}
    .subhead {color:var(--text-color, #742d23); font-size:1.05rem; margin-bottom:1.8rem}
    div[data-testid="stMetric"] {background:#f4f7fb; border:1px solid #dae4ee; border-radius:12px; padding:14px 16px;}
    /* Las tarjetas mantienen el fondo claro tanto en modo oscuro como claro. */
    div[data-testid="stMetric"] {color:#14253b !important;}
    div[data-testid="stMetric"] * {color:#14253b !important; opacity:1 !important;}
    div[data-testid="stMetricLabel"],
    div[data-testid="stMetricLabel"] *,
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] *,
    div[data-testid="stMetricDelta"] * {color:#14253b !important; opacity:1 !important;}
    div[data-testid="stMetricLabel"] {font-weight:600 !important;}
    div[data-testid="stMetricValue"] {font-weight:800 !important;}
    .note, .note * {color:#14253b !important;}
    .note {background:#eef5fa; border-left:4px solid #2b83a4; padding:12px 14px; border-radius:5px; margin:12px 0}
</style>
""", unsafe_allow_html=True)


def originales():
    return json.loads(json.dumps(DATOS_ORIGINALES, ensure_ascii=False))


def reiniciar():
    st.session_state.datos_ccc = originales()
    st.session_state.revision = st.session_state.get("revision", 0) + 1
    st.session_state.resultado_ccc = None


if "datos_ccc" not in st.session_state:
    reiniciar()

st.markdown('<div class="eyebrow">INVESTIGACIÓN DE OPERACIONES </div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">Cosmic Computer Company</div>', unsafe_allow_html=True)
st.markdown('<div class="subhead">Calculadora de ubicación de plantas y distribución de computadoras </div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Panel de control")
    st.write("Modifica los datos, pulsa **Resolver** y descubre qué plantas conviene abrir y cuántas computadoras enviar.")
    if st.button("↺ Restablecer valores del libro", use_container_width=True):
        reiniciar()
        st.rerun()
    st.divider()
    st.markdown("**Modelo matemático**")
    st.latex(r"\min Z=\sum_i F_i y_i+\sum_i\sum_j c_{ij}x_{ij}")
    st.latex(r"\sum_j x_{ij}\leq C_i y_i")
    st.latex(r"\sum_i x_{ij}=D_j")
    st.caption("Las cantidades enviadas son enteras y las decisiones de apertura son binarias.")
    st.divider()

state = st.session_state.datos_ccc
revision = st.session_state.revision
p = state["plantas"]
t = state["tiendas"]

st.subheader("Editar los datos")
a, b = st.columns(2, gap="large")
with a:
    st.markdown("**Plantas de producción**")
    plantas_df = pd.DataFrame({"Planta":p, "Capacidad":state["capacidades"], "Costo fijo ($)":state["costos_fijos"]})
    edit_plantas = st.data_editor(
        plantas_df, hide_index=True, use_container_width=True, num_rows="fixed", key=f"plantas_{revision}",
        disabled=["Planta"],
        column_config={
            "Planta": st.column_config.TextColumn("Planta"),
            "Capacidad": st.column_config.NumberColumn("Capacidad", min_value=0, step=1, format="%d"),
            "Costo fijo ($)": st.column_config.NumberColumn("Costo fijo ($)", min_value=0.0, step=1000.0),
        },
    )
with b:
    st.markdown("**Tiendas y demandas**")
    demanda_df = pd.DataFrame({"Tienda":t, "Demanda":state["demandas"]})
    edit_demanda = st.data_editor(
        demanda_df, hide_index=True, use_container_width=True, num_rows="fixed", key=f"demanda_{revision}",
        disabled=["Tienda"],
        column_config={"Demanda":st.column_config.NumberColumn("Demanda",min_value=0,step=1,format="%d")},
    )

st.markdown("**Costos de transporte por computadora (planta → tienda)**")
transport_df = pd.DataFrame(state["transportes"], index=p, columns=t)
transport_df.index.name = "Planta"
edit_transport = st.data_editor(
    transport_df, use_container_width=True, num_rows="fixed", key=f"transporte_{revision}",
    column_config={name:st.column_config.NumberColumn(name, min_value=0.0, step=1.0) for name in t},
)

try:
    data = {
        "plantas":p, "tiendas":t,
        "capacidades":[int(x) for x in edit_plantas["Capacidad"].tolist()],
        "costos_fijos":[float(x) for x in edit_plantas["Costo fijo ($)"].tolist()],
        "demandas":[int(x) for x in edit_demanda["Demanda"].tolist()],
        "transportes":edit_transport[t].astype(float).values.tolist(),
    }
    # Reject nonintegers in capacity/demand instead of silently truncating.
    if any(float(a) != int(a) for a in edit_plantas["Capacidad"].tolist() + edit_demanda["Demanda"].tolist()):
        raise ValueError("La capacidad y la demanda deben ser números enteros.")
    if any(pd.isna(edit_plantas[col]).any() for col in ["Capacidad","Costo fijo ($)"]) or edit_demanda["Demanda"].isna().any() or edit_transport.isna().any().any():
        raise ValueError("Completa las celdas vacías antes de resolver.")
    capacidad_total = sum(data["capacidades"])
    demanda_total = sum(data["demandas"])
    x, y = st.columns(2)
    x.metric("Capacidad máxima disponible", f"{capacidad_total:,}".replace(",","."))
    y.metric("Demanda total", f"{demanda_total:,}".replace(",","."))
except (ValueError, TypeError, OverflowError) as exc:
    data = None
    st.error(f"Revisa los datos ingresados: {exc}")

with st.container():
    if st.button("▶ Resolver problema y calcular el costo mínimo", type="primary", use_container_width=True, disabled=data is None):
        st.session_state.resultado_ccc = (json.loads(json.dumps(data)), resolver(data))

stored = st.session_state.resultado_ccc
if stored is None:
    st.info("Pulsa **Resolver problema** para obtener la solución. Puedes modificar cualquier valor y volver a calcular.")
else:
    resolved_data, result = stored
    st.divider()
    st.subheader("Resultado óptimo")
    if "error" in result:
        st.error(result["error"])
        st.write("El sistema no inventa una respuesta: revisa la capacidad disponible y la demanda o los datos numéricos.")
    else:
        f1, f2, f3 = st.columns(3)
        f1.metric("Costo mínimo total", moneda(result["total"]))
        f2.metric("Costos fijos", moneda(result["fijos"]))
        f3.metric("Costos de transporte", moneda(result["transporte"]))
        st.success("Se encontró una solución óptima que satisface todas las restricciones.")

        st.markdown("**¿Qué plantas deben abrirse?**")
        estado = pd.DataFrame({
            "Planta":resolved_data["plantas"],
            "Estado":["ABIERTA" if int(v) else "CERRADA" for v in result["abiertas"]],
            "Capacidad":resolved_data["capacidades"],
            "Unidades enviadas":result["envios"].sum(axis=1).tolist(),
        })
        st.dataframe(estado, hide_index=True, use_container_width=True)
        st.markdown("**Distribución óptima entre plantas y tiendas**")
        envios_df = pd.DataFrame(result["envios"], index=resolved_data["plantas"], columns=resolved_data["tiendas"])
        envios_df.index.name="Planta"
        envios_df["Total enviado"] = envios_df.sum(axis=1)
        fila_total = envios_df.sum(axis=0).to_frame().T
        fila_total.index=["TOTAL RECIBIDO"]
        tabla = pd.concat([envios_df,fila_total])
        st.dataframe(tabla, use_container_width=True)
        st.markdown("**Comprobación de la demanda por tienda**")
        verific = pd.DataFrame({
            "Tienda":resolved_data["tiendas"],
            "Solicitado":resolved_data["demandas"],
            "Recibido":result["envios"].sum(axis=0).tolist(),
        })
        verific["Cumple"] = verific["Solicitado"] == verific["Recibido"]
        st.dataframe(verific,hide_index=True,use_container_width=True)
        st.markdown("**Detalle de gastos de transporte**")
        detalles=[]
        for i, planta in enumerate(resolved_data["plantas"]):
            for j, tienda in enumerate(resolved_data["tiendas"]):
                n=int(result["envios"][i,j])
                if n>0:
                    costo=float(resolved_data["transportes"][i][j])
                    detalles.append({"Origen":planta,"Destino":tienda,"Unidades":n,"Costo por unidad":costo,"Costo transporte":n*costo})
        st.dataframe(pd.DataFrame(detalles),hide_index=True,use_container_width=True)
        st.markdown(f'<div class="note">Costo mínimo = costos fijos ({moneda(result["fijos"])}) + transporte ({moneda(result["transporte"])}) = <b>{moneda(result["total"])}</b></div>',unsafe_allow_html=True)

        buf=io.StringIO()
        tabla.to_csv(buf, index=True)
        st.download_button("⬇ Descargar tabla de distribución (CSV)",buf.getvalue().encode("utf-8-sig"),"distribucion_CCC.csv","text/csv",use_container_width=True)
