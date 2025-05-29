import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns

# Configuración de la página
st.set_page_config(page_title="Análisis de Llamadas", layout="wide")
sns.set(style="whitegrid")

# Cargar archivo
archivo_excel = "AppInfo.xlsx"
df = pd.read_excel(archivo_excel, engine="openpyxl")

# Normalizar nombres
mapeo_a_nombre_completo = {
    "Jorge": "Jorge Cesar Flores Rivera",
    "Maria": "Maria Teresa Loredo Morales",
    "Jonathan": "Jonathan Alejandro Zúñiga",
}
df["Agent Name"] = df["Agent Name"].replace(mapeo_a_nombre_completo)

# Procesamiento de columnas de fecha y tiempo
df["Call Start Time"] = pd.to_datetime(df["Call Start Time"], errors="coerce")
df["Call End Time"] = pd.to_datetime(df["Call End Time"], errors="coerce")
df = df.dropna(subset=["Call Start Time"])

df["Talk Time"] = pd.to_timedelta(df["Talk Time"], errors="coerce")
df["Duración (min)"] = df["Talk Time"].dt.total_seconds() / 60
df["Duración (min)"] = df["Duración (min)"].fillna(0)

# Columnas adicionales
df["Fecha"] = df["Call Start Time"].dt.date
df["Hora"] = df["Call Start Time"].dt.hour
df["DíaSemana_En"] = df["Call Start Time"].dt.day_name()
dias_traducidos = {
    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
}
df["DíaSemana"] = df["DíaSemana_En"].map(dias_traducidos)

# Identificar llamadas perdidas
df["LlamadaPerdida"] = df["Talk Time"] == pd.Timedelta("0:00:00")

# Asignar agentes para llamadas perdidas por horario
def agentes_por_horario(hora):
    if 8 <= hora < 10:
        return ["Jorge Cesar Flores Rivera"]
    elif 10 <= hora < 12:
        return ["Jorge Cesar Flores Rivera", "Maria Teresa Loredo Morales"]
    elif 12 <= hora < 16:
        return ["Jorge Cesar Flores Rivera", "Maria Teresa Loredo Morales", "Jonathan Alejandro Zúñiga"]
    elif 16 <= hora < 18:
        return ["Jonathan Alejandro Zúñiga", "Maria Teresa Loredo Morales"]
    elif 18 <= hora < 20:
        return ["Jonathan Alejandro Zúñiga"]
    else:
        return []

# Expandir llamadas perdidas con agentes asignados
filas = []
for _, row in df.iterrows():
    if row["LlamadaPerdida"]:
        agentes = agentes_por_horario(row["Hora"])
        if agentes:
            for agente in agentes:
                filas.append({**row, "AgenteFinal": agente})
        else:
            if pd.notna(row["Agent Name"]):
                filas.append({**row, "AgenteFinal": row["Agent Name"]})
    else:
        if pd.notna(row["Agent Name"]):
            filas.append({**row, "AgenteFinal": row["Agent Name"]})

df_expandido = pd.DataFrame(filas)
df_expandido = df_expandido[df_expandido["AgenteFinal"].notna()]

# Streamlit UI
st.title("📞 Análisis Integral de Productividad y Llamadas")

# Filtros de fecha
fecha_min = df["Fecha"].min()
fecha_max = df["Fecha"].max()
fecha_inicio, fecha_fin = st.date_input("Selecciona un rango de fechas:", [fecha_min, fecha_max])
df_filtrado = df[(df["Fecha"] >= fecha_inicio) & (df["Fecha"] <= fecha_fin)].copy()
df_expandido_filtrado = df_expandido[(df_expandido["Fecha"] >= fecha_inicio) & (df_expandido["Fecha"] <= fecha_fin)].copy()

# Módulo 1: resumen general
st.subheader("📊 Resumen de llamadas por agente")
resumen = df_expandido_filtrado.groupby("AgenteFinal").agg(
    Total_Llamadas=("LlamadaPerdida", "count"),
    Llamadas_Perdidas=("LlamadaPerdida", "sum"),
    Duración_Total_Min=("Duración (min)", "sum"),
    Duración_Promedio_Min=("Duración (min)", "mean"),
)
resumen["% Perdidas"] = resumen["Llamadas_Perdidas"] / resumen["Total_Llamadas"] * 100
st.dataframe(resumen.style.format({"Duración_Total_Min": "{:.1f}", "Duración_Promedio_Min": "{:.1f}", "% Perdidas": "{:.1f}%"}))

# Módulo 2: distribución por día de la semana
st.subheader("📅 Distribución de llamadas por día de la semana")
fig1, ax1 = plt.subplots()
sns.countplot(data=df_expandido_filtrado, x="DíaSemana", order=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"], ax=ax1)
plt.xticks(rotation=45)
plt.title("Cantidad de llamadas por día")
st.pyplot(fig1)

# Módulo 3: heatmap por hora y día
st.subheader("🕒 Llamadas por hora y día (Heatmap)")
pivot = df_expandido_filtrado.pivot_table(index="Hora", columns="DíaSemana", values="Duración (min)", aggfunc="count", fill_value=0)
pivot = pivot[["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"]]
fig2, ax2 = plt.subplots(figsize=(10, 6))
sns.heatmap(pivot, annot=True, fmt=".0f", cmap="YlGnBu", ax=ax2)
plt.title("Distribución de llamadas por hora y día")
st.pyplot(fig2)

# Módulo 4: alertas de llamadas perdidas
st.subheader("🚨 Alertas de días con muchas llamadas perdidas")
alertas = df_expandido_filtrado.groupby("Fecha")["LlamadaPerdida"].sum().reset_index()
dias_alerta = alertas[alertas["LlamadaPerdida"] > alertas["LlamadaPerdida"].mean() + 1.5 * alertas["LlamadaPerdida"].std()]
if not dias_alerta.empty:
    st.warning("Días con llamadas perdidas por encima del promedio:")
    st.dataframe(dias_alerta)
else:
    st.success("No hay días críticos detectados.")

# Opcional: descarga de resultados
st.subheader("⬇️ Descargar datos")
csv = df_expandido_filtrado.to_csv(index=False).encode("utf-8")
st.download_button("Descargar CSV", csv, "llamadas_filtradas.csv", "text/csv")
