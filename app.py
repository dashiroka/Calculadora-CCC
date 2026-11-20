"""Calculadora web CCC. Ejecutar: streamlit run app.py"""
import io
import json
import traceback

import pandas as pd
import streamlit as st
from solver_ccc import DATOS_ORIGINALES, resolver, moneda

st.set_page_config(page_title="Calculadora CCC", page_icon="🏭", layout="wide")
st.markdown("""
<style>
.block-container {max-width:1250px; padding-top:1.5rem;}
div[data-testid="stMetric"] {background:#f3f6fb!important; border:1px solid #d4dce8;
 border-radius:14px; padding:16px 20px;}
div[data-testid="stMetric"] *, div[data-testid="stMetric"] {color:#14263b!important;opacity:1!important;}
div[data-testid="stMetricValue"] {font-weight:800!important;}
.ccc-help {background:#eaf2fa;color:#15304b;border-radius:10px;padding:14px;margin:12px 0}
</style>
""", unsafe_allow_html=True)


def copia_original():
    return json.loads(json.dumps(DATOS_ORIGINALES, ensure_ascii=False))


def recalcular(datos):
    try:
        resultado = resolver(datos)
        return {"datos": datos, "resultado": resultado, "error_tecnico": None}
    except Exception as exc:
        return {"datos": datos, "resultado": None, "error_tecnico": f"{type(exc).__name__}: {exc}"}


def restaurar():
    st.session_state.ccc_datos = copia_original()
    st.session_state.ccc_revision = st.session_state.get("ccc_revision",0) + 1
    st.session_state.ccc_salida = recalcular(st.session_state.ccc_datos)


if "ccc_datos" not in st.session_state:
    restaurar()

st.title("🏭 Cosmic Computer Company")
st.write("**Calculadora de ubicación de plantas — Ejemplo 8.4**")
st.caption("Modifica los valores y pulsa Resolver. La solución original aparece desde el inicio.")

with st.sidebar:
    st.header("⚙️ Panel de control")
    st.write("Puedes modificar capacidades, demandas, costos fijos y de transporte.")
    if st.button("↺ Restablecer valores del libro",use_container_width=True):
        restaurar()
        st.rerun()
    st.divider()
    st.markdown("**Modelo matemático**")
    st.latex(r"\min Z=\sum_i F_i y_i+\sum_i\sum_j c_{ij}x_{ij}")
    st.latex(r"\sum_j x_{ij}\le C_i y_i")
    st.latex(r"\sum_i x_{ij}=D_j")
    st.caption("Variables de apertura binarias; envíos enteros no negativos.")

base = st.session_state.ccc_datos
revision = st.session_state.ccc_revision
p = base["plantas"]
t = base["tiendas"]
st.subheader("01 · Datos del ejercicio")
# El formulario asegura que los cambios en las tablas se envían junto al clic.
with st.form(key=f"formulario_ccc_{revision}", clear_on_submit=False):
    col1,col2 = st.columns(2,gap="large")
    with col1:
        st.markdown("**Plantas: capacidad y costo fijo**")
        df_p = pd.DataFrame({"Planta":p,"Capacidad":base["capacidades"],"Costo fijo ($)":base["costos_fijos"]})
        ep = st.data_editor(df_p,hide_index=True, use_container_width=True,num_rows="fixed",disabled=["Planta"],
             column_config={"Capacidad":st.column_config.NumberColumn("Capacidad",min_value=0,step=1,format="%d"),
                            "Costo fijo ($)":st.column_config.NumberColumn("Costo fijo ($)",min_value=0.0,step=1000.0)},
             key=f"plantas_{revision}")
    with col2:
        st.markdown("**Tiendas: demanda mensual**")
        df_d = pd.DataFrame({"Tienda":t,"Demanda":base["demandas"]})
        ed = st.data_editor(df_d,hide_index=True,use_container_width=True,num_rows="fixed",disabled=["Tienda"],
             column_config={"Demanda":st.column_config.NumberColumn("Demanda",min_value=0,step=1,format="%d")},
             key=f"demandas_{revision}")
    st.markdown("**Costos de transporte por computadora**")
    df_c = pd.DataFrame(base["transportes"],columns=t)
    df_c.insert(0,"Planta",p)
    ec = st.data_editor(df_c,hide_index=True,use_container_width=True,num_rows="fixed",disabled=["Planta"],
            column_config={name:st.column_config.NumberColumn(name,min_value=0.0,step=1.0) for name in t},
            key=f"costos_{revision}")
    enviado = st.form_submit_button("▶ Resolver problema y calcular el costo mínimo",type="primary",use_container_width=True)

if enviado:
    try:
        valores_c = ep["Capacidad"].tolist()
        valores_d = ed["Demanda"].tolist()
        if any(pd.isna(x) for x in valores_c + valores_d + ep["Costo fijo ($)"].tolist()) or ec[t].isna().any().any():
            raise ValueError("Hay celdas vacías. Completa todas las tablas.")
        if any(float(v)!=int(float(v)) for v in valores_c+valores_d):
            raise ValueError("Las capacidades y las demandas deben ser números enteros.")
        datos = {"plantas":p,"tiendas":t,
                 "capacidades":[int(v) for v in valores_c],
                 "costos_fijos":[float(v) for v in ep["Costo fijo ($)"].tolist()],
                 "demandas":[int(v) for v in valores_d],
                 "transportes":ec[t].astype(float).values.tolist()}
        st.session_state.ccc_datos = datos
        st.session_state.ccc_salida = recalcular(datos)
    except Exception as exc:
        st.session_state.ccc_salida = {"datos":base,"resultado":None,"error_tecnico":str(exc)}

salida = st.session_state.ccc_salida
datos = salida["datos"]
r = salida["resultado"]
st.divider()
st.subheader("02 · Resultado de la optimización")
if enviado:
    st.success("Se recibieron los datos y se ejecutó el cálculo.") if r is not None and "error" not in r else None
if salida["error_tecnico"]:
    st.error("No se pudo completar el cálculo: " + salida["error_tecnico"])
    st.info("Comprueba que todos los campos sean numéricos y que las capacidades y demandas sean enteras.")
elif "error" in r:
    st.warning(r["error"])
else:
    a,b,c = st.columns(3)
    a.metric("Costo mínimo total",moneda(r["total"]))
    b.metric("Costos fijos",moneda(r["fijos"]))
    c.metric("Costos de transporte",moneda(r["transporte"]))
    st.markdown("**Plantas abiertas y cerradas**")
    estado = pd.DataFrame({"Planta":datos["plantas"],
               "Decisión":["ABIERTA" if y else "CERRADA" for y in r["abiertas"]],
               "Capacidad":datos["capacidades"],
               "Enviado":[int(z) for z in r["envios"].sum(axis=1)]})
    st.dataframe(estado,hide_index=True,use_container_width=True)
    st.markdown("**Unidades a enviar desde cada planta hasta cada tienda**")
    tabla = pd.DataFrame(r["envios"],columns=datos["tiendas"],index=datos["plantas"])
    tabla.index.name="Planta"
    tabla["TOTAL ENVIADO"] = tabla.sum(axis=1)
    total = tabla.sum(axis=0)
    tabla.loc["TOTAL RECIBIDO"] = total
    st.dataframe(tabla,use_container_width=True)
    st.markdown("**Comprobación de las demandas**")
    verific = pd.DataFrame({"Tienda":datos["tiendas"],"Solicitado":datos["demandas"],
                "Recibido":[int(v) for v in r["envios"].sum(axis=0)]})
    verific["Cumple"] = verific["Solicitado"] == verific["Recibido"]
    st.dataframe(verific,hide_index=True,use_container_width=True)
    st.markdown("**Detalle de costos de envío**")
    filas=[]
    for i,planta in enumerate(datos["plantas"]):
        for j,tienda in enumerate(datos["tiendas"]):
            unidades=int(r["envios"][i,j])
            if unidades:
                costo=float(datos["transportes"][i][j])
                filas.append({"Origen":planta,"Destino":tienda,"Unidades":unidades,
                              "Costo unitario":costo,"Subtotal":unidades*costo})
    if filas:
        st.dataframe(pd.DataFrame(filas),hide_index=True,use_container_width=True)
    st.markdown(f'<div class="ccc-help"><b>Resultado:</b> {moneda(r["fijos"])} (fijos) + {moneda(r["transporte"])} (transporte) = <b>{moneda(r["total"])}</b></div>',unsafe_allow_html=True)
    st.download_button("⬇ Descargar distribución CSV",tabla.to_csv().encode("utf-8-sig"),
                       file_name="distribucion_CCC.csv",mime="text/csv")

st.caption("Fuente: Mathur y Solow (1996), Ejemplo 8.4. Cálculos mediante programación entera mixta (SciPy/HiGHS).")
