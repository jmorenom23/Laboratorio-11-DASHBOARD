import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

df_clientes = pd.read_csv("KORA_clientes.csv", parse_dates=["fecha_registro"])
df_pedidos = pd.read_csv("KORA_pedidos.csv", parse_dates=["fecha_pedido"])

assert df_clientes.id_cliente.is_unique
assert df_pedidos.id_pedido.is_unique

st.set_page_config(layout="wide")
st.title("KORA | Clientes")
st.caption("Elaborado con datos de clientes")
st.sidebar.header("FILTROS")

filtro_canal = st.sidebar.multiselect(label="CANALES",
                                      options=df_clientes.canal_adquisicion.unique(),
                                      default=df_clientes.canal_adquisicion.unique())

filtro_ciudad = st.sidebar.multiselect(label="CIUDAD",
                                       options=df_clientes.ciudad.unique(),
                                       default=df_clientes.ciudad.unique())

filtro_segmento = st.sidebar.multiselect(label="SEGMENTO",
                                         options=["Sin Compra", "Primerizo", "En Desarrollo", "Fiel", "En Pausa"],
                                         default=["Sin Compra", "Primerizo", "En Desarrollo", "Fiel", "En Pausa"])


filtro_preferencia = st.sidebar.multiselect(label="PREFERENCIA DECLARADA",
                                            options=df_clientes.preferencia_declarada.unique(),
                                            default=df_clientes.preferencia_declarada.unique())

df_intermedio = (df_pedidos.groupby("id_cliente", as_index=False)
                 .agg(n_pedidos=("id_pedido", "nunique"),
                      ingreso_total=("ingreso_neto_cop", "sum"),
                      fecha_ultimo_pedido=("fecha_pedido", "max"))
                 )


fecha_corte = pd.Timestamp("2026-10-31")
df_intermedio["resencia"] = (fecha_corte - df_intermedio["fecha_ultimo_pedido"]).dt.days


def asignar_segmento(n_pedidos, tiempo):
    segmento = ""
    if n_pedidos == 0:
        segmento = "Sin Compra"
    elif n_pedidos == 1 and tiempo <= 90:
        segmento = "Primerizo"
    elif n_pedidos == 2 and tiempo <= 90:
        segmento = "En Desarrollo"
    elif n_pedidos >= 3 and tiempo <= 90:
        segmento = "Fiel"
    elif n_pedidos >= 1 and tiempo > 90:
        segmento = "En Pausa"
    return segmento


df_intermedio["segmento"] = (df_intermedio
                             .apply(lambda x: asignar_segmento
                                    (x["n_pedidos"], x["resencia"]), axis=1)
                             )

df_clientes_filtrado = df_clientes[(df_clientes.canal_adquisicion.isin(filtro_canal))
                                   & (df_clientes.ciudad.isin(filtro_ciudad))
                                   & (df_clientes.preferencia_declarada.isin(filtro_preferencia))]
df_final = df_clientes_filtrado.merge(df_intermedio, how="left", on="id_cliente", validate="one_to_one")
df_final["segmento"] = df_final["segmento"].fillna("Sin Compra")
df_final["n_pedidos"] = df_final["n_pedidos"].fillna(0)
df_final["ingreso_total"] = df_final["ingreso_total"].fillna(0)
df_final = df_final[df_final.segmento.isin(filtro_segmento)]


df_compradores = df_final.query("n_pedidos > 0")
compradores = df_compradores.shape[0]
pedidos = int(df_final.n_pedidos.sum())
ingreso = df_final.ingreso_total.sum()
una_compra = df_final.query("n_pedidos == 1").shape[0]

if compradores > 0:
    recompra = f"{df_final.query('n_pedidos > 1').shape[0] / compradores * 100 :.2f}%"
    pct_una_compra = f"{una_compra / compradores * 100 :.2f}%"
else:
    recompra = "N/A"
    pct_una_compra = "N/A"
    st.warning("No hay compradores con los filtros seleccionados.")

a, b, c, d = st.columns(4)
a.metric(label="COMPRADORES", value=compradores, border=True)
b.metric(label="PEDIDOS", value=pedidos, border=True)
c.metric(label="INGRESO", value=f"{ingreso/1e6:.1f} M", border=True)
d.metric(label="RECOMPRA", value=recompra, border=True)

e, f, g, h = st.columns(4)
e.metric(label="CLIENTES CON 1 COMPRA", value=una_compra, border=True)
f.metric(label="% COMPRADORES CON 1 COMPRA", value=pct_una_compra, border=True)

st.divider()

derecha, izquierda = st.columns(2)

with derecha:
    df_plot = (df_final.groupby("segmento", as_index=False)
               .agg(n_clientes=("id_cliente", "count")))
    fig = px.bar(data_frame=df_plot, x="segmento", y="n_clientes", color="segmento", 
                 color_discrete_map={"En Desarrollo": "#57c9c3",
                                             "En Pausa": "#07709A",
                                             "Fiel": "#1E8D0F",
                                             "Primerizo": "#176226",
                                             "Sin Compra": "#371762"}, text="n_clientes")
    fig.update_layout(xaxis_title="Segmento", yaxis_title="Número de Clientes", showlegend=False)
    st.plotly_chart(fig, width="stretch")

with izquierda:
    df_plot = (df_final.groupby("preferencia_declarada", as_index=False)
               .agg(ingreso=("ingreso_total", "sum")).sort_values(by="ingreso", ascending=False))
    fig = px.bar(data_frame=df_plot, x="ingreso", y="preferencia_declarada", orientation="h",  color="preferencia_declarada", 
                 color_discrete_map={"Papelería": "#E8A0BF",
                                                 "Cuidado personal": "#E8A0BF",
                                                 "Deporte": "#81B29A",
                                                 "Hogar": "#E07A5F",
                                                 "Tecnología": "#6EC1E4"})
    fig.update_layout(xaxis_title="Ingreso", yaxis_title="Preferencia declarada", showlegend=False)
    st.plotly_chart(fig, width="stretch")

st.divider()
st.header("Laboratorio 11")


st.subheader("1. ¿Por qué la tasa de recompra sola no basta?")
st.markdown("""
            La tasa de recompra la medimos como el porcentaje de compradores que hicieron dos o más pedidos,
            dividiendo entre quienes ya compraron al menos una vez. Por otra parte, el número de clientes con exactamente 
            una compra nos dice cuántas personas podrían recibir la campaña, pues mirar solo la tasa puede engañarnos,
            ya que un canal puede tener la tasa más baja, pero si tiene pocos clientes, el piloto movería muy poco. 
            Además, una tasa calculada con pocas personas puede cambiar mucho con unos pocos casos, por esta razon necesitamos ver las dos cosas juntas,
            dónde hay espacio para mejorar y a cuántas personas podemos llegar.
""")

df_compradores = df_compradores.copy()
df_compradores["recompra"] = df_compradores.n_pedidos >= 2
df_compradores["una_compra"] = df_compradores.n_pedidos == 1
df_canal = (df_compradores.groupby("canal_adquisicion", as_index=False)
            .agg(compradores=("id_cliente", "count"),
                 tasa_recompra=("recompra", "mean"),
                 clientes_una_compra=("una_compra", "sum")))
df_canal["tasa_recompra"] = (df_canal.tasa_recompra * 100).round(1)

if df_canal.shape[0] == 0:
    st.warning("No hay compradores con los filtros seleccionados: los gráficos del laboratorio están vacíos.")
else:
    graf1, graf2 = st.columns(2)

    # Punto 3
    with graf1:
        st.subheader("3. Tasa de recompra por canal")
        df_plot = df_canal.sort_values(by="tasa_recompra").copy()
        df_plot["etiqueta"] = (df_plot.tasa_recompra.astype(str) + "% (n=" + df_plot.compradores.astype(str) + ")")
        fig = px.bar(data_frame=df_plot, x="tasa_recompra", y="canal_adquisicion", orientation="h",
                     text="etiqueta", hover_data=["compradores"], color="canal_adquisicion",
                     color_discrete_map={"Redes sociales": "#a7c957",
                                         "Búsqueda": "#6A994E",
                                         "Referidos": "#386641",
                                         "Orgánico": "#1B7E2F"})
        fig.update_layout(xaxis_title="% de compradores con 2+ pedidos", yaxis_title="Canal", showlegend=False)
        st.plotly_chart(fig, width="stretch")
        st.markdown("""
**Justificación del gráfico:** Escogimos las barras horizontales porque nos permiten comparar mejor los resultados de cada canal. Al organizarlas de menor a mayor, podemos identificar fácilmente cuál tiene la tasa de recompra más baja y cuál la más alta. No utilizamos un gráfico de torta porque los canales no representan partes de un mismo total, ni uno de líneas porque no estamos analizando cambios en el tiempo. También mostramos la cantidad de compradores de cada canal.
""")

    # Punto 4
    with graf2:
        st.subheader("4. Clientes con exactamente un pedido por canal")
        df_plot = df_canal.sort_values(by="clientes_una_compra")
        fig = px.bar(data_frame=df_plot, x="clientes_una_compra", y="canal_adquisicion", orientation="h",
                     text="clientes_una_compra", color="canal_adquisicion",
                     color_discrete_map={"Redes sociales": "#a7c957",
                                         "Búsqueda": "#6A994E",
                                         "Referidos": "#386641",
                                         "Orgánico": "#1B7E2F"})
        fig.update_layout(xaxis_title="Clientes con 1 pedido", yaxis_title="Canal", showlegend=False)
        st.plotly_chart(fig, width="stretch")
        st.markdown("""
**¿El canal con mayor volumen coincide necesariamente con el de menor tasa de recompra?**
**No, no necesariamente.** El volumen de clientes con un solo pedido depende del tamaño del canal, mientras que la tasa de recompra es una proporción. En los datos completos Redes sociales tiene el mayor volumen (147) y la menor tasa (59,6 %), pero el orden no se mantiene en el resto: Búsqueda tiene más clientes de un pedido que Referidos (83 vs. 74) y, sin embargo, una tasa mayor (68,3 % vs. 65,7 %). Un canal grande puede tener una buena tasa y aun así acumular muchos clientes de un pedido, y uno pequeño puede tener tasa baja con pocos clientes por impactar.
""")

# Punto 5
st.subheader("5. Comprobación de los filtros")
st.markdown("""
Probamos los filtros con dos selecciones y las métricas y ambos gráficos se actualizan:

| Selección | Compradores | % recompra | Clientes con 1 compra | % con 1 compra |
|---|---|---|---|---|
| Ciudad = Bogotá | 513 | 67,06 % | 169 | 32,94 % |
| Preferencia = Tecnología | 249 | 66,67 % | 83 | 33,33 % |

Si no hay compradores, el tablero muestra una advertencia y N/A, sin errores.
""")

# Punto 6
st.subheader("6. Recomendación")
st.markdown("""
Creemos que lo mejor sería empezar el piloto en Redes sociales, ya que encontramos 147 clientes que solo hicieron una compra y es el canal con la tasa de recompra más baja (59,6 %). Esto nos hace pensar que es donde hay más oportunidades de mejorar. Sin embargo, los datos no nos dicen por qué esos clientes no volvieron a comprar. Por eso, para saber si el piloto funciona, compararíamos la tasa de recompra con la de otro grupo de clientes del mismo canal que no participe en el piloto.
""")