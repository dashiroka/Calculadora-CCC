    st.caption("Basado en el ejemplo del libro de Mathur y Solow (1996). Sin necesidad de instalar Python para los visitantes una vez publicado.")

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

st.markdown("**Costos de transporte por computadora)**")
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
