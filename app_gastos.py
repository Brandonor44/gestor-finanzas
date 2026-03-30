import streamlit as st
from supabase import create_client, Client
import plotly.express as px
import pandas as pd
import datetime
from calendar import monthrange

# --- INICIALIZAR MEMORIA TEMPORAL ---
if 'confirmando' not in st.session_state:
    st.session_state.confirmando = False
if 'datos_temp' not in st.session_state:
    st.session_state.datos_temp = None
if 'mensaje_exito' not in st.session_state:
    st.session_state.mensaje_exito = None
if 'form_key' not in st.session_state:
    st.session_state.form_key = 0

st.set_page_config(page_title="Finanzas ASIR", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("🚀 Sistema de Gestión Financiera - Brandon Edition")

if st.session_state.mensaje_exito:
    st.success(st.session_state.mensaje_exito)
    st.session_state.mensaje_exito = None

# --- LÓGICA DE DATOS ---
def obtener_categorias(tipo):
    if tipo == "INGRESO":
        res = supabase.table("categorias").select("id, nombre").eq("id_padre", 1).eq("nivel", 2).execute()
    else:
        res = supabase.table("categorias").select("id, nombre").eq("nivel", 4).execute()
    return {item['nombre']: item['id'] for item in res.data}

def mostrar_metricas():
    hoy = datetime.date.today()
    primer_dia = hoy.replace(day=1)
    ultimo_dia = hoy.replace(day=monthrange(hoy.year, hoy.month)[1])
    
    res = supabase.table("registros").select("importe, categoria_id").gte("fecha", str(primer_dia)).lte("fecha", str(ultimo_dia)).execute()
    
    cat_ingresos = supabase.table("categorias").select("id").eq("id_padre", 1).execute()
    ids_ingresos = [c['id'] for c in cat_ingresos.data]
    
    total_ingresos = 0.0
    total_gastos = 0.0
    
    for r in res.data:
        if r['categoria_id'] in ids_ingresos:
            total_ingresos += r['importe']
        else:
            total_gastos += r['importe']
            
    balance = total_ingresos - total_gastos
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Ingresos del Mes", f"{total_ingresos:,.2f} €")
    col2.metric("🔴 Gastos del Mes", f"{total_gastos:,.2f} €")
    col3.metric("⚖️ Resultado Neto", f"{balance:,.2f} €")

def mostrar_graficos():
    hoy = datetime.date.today()
    primer_dia = hoy.replace(day=1)
    
    res = (supabase.table("registros")
           .select("importe, categoria_id, categorias(nombre)")
           .gte("fecha", str(primer_dia))
           .execute())
    
    if res.data:
        cat_ingresos = supabase.table("categorias").select("id").eq("id_padre", 1).execute()
        ids_ingresos = [c['id'] for c in cat_ingresos.data]
        
        gastos_data = []
        for r in res.data:
            if r['categoria_id'] not in ids_ingresos:
                gastos_data.append({
                    "Categoría": r['categorias']['nombre'],
                    "Importe": r['importe']
                })
        
        if gastos_data:
            df_gastos = pd.DataFrame(gastos_data)
            df_resumen = df_gastos.groupby("Categoría")["Importe"].sum().reset_index()
            
            fig = px.pie(
                df_resumen, 
                values='Importe', 
                names='Categoría', 
                hole=0.5,
                title="📊 Distribución de Gastos (Mes Actual)",
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            # Ajustamos los márgenes para que encaje bien en la columna
            fig.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aún no hay gastos este mes para generar el gráfico.")

# --- RENDERIZADO PRINCIPAL ---
mostrar_metricas()
st.divider()

# CREAMOS LAS DOS COLUMNAS PRINCIPALES
col_izq, col_der = st.columns([1, 1], gap="large")

with col_izq:
    st.subheader("📝 Nuevo Registro")
    tipo_mov = st.radio("Tipo de movimiento:", ["GASTO", "INGRESO"], horizontal=True)
    cat_dict = obtener_categorias(tipo_mov)

    with st.form(f"registro_form_{st.session_state.form_key}", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        with col_a:
            concepto = st.text_input("Concepto", placeholder="nuevo registro")
            fecha = st.date_input("Fecha")
        with col_b:
            importe = st.number_input("Importe (€)", min_value=0.01, step=0.1, value=None, placeholder="0,00")
            categoria_sel = st.selectbox("Categoría", options=list(cat_dict.keys()))
        
        detalles = st.text_input("Detalles / Comentarios (Opcional)")
        
        submit = st.form_submit_button("Registrar")

        if submit:
            if importe is None:
                st.error("⚠️ Por favor, introduce un importe válido antes de continuar.")
            elif not concepto:
                st.error("⚠️ Por favor, introduce un concepto.")
            else:
                st.session_state.datos_temp = {
                    "concepto": concepto,
                    "importe": importe,
                    "categoria_id": cat_dict[categoria_sel],
                    "nombre_categoria": categoria_sel,
                    "fecha": str(fecha),
                    "tipo": tipo_mov,
                    "detalles": detalles
                }
                st.session_state.confirmando = True
                st.rerun()

with col_der:
    # EL GRÁFICO SE DIBUJA AQUÍ, AL LADO DEL FORMULARIO
    mostrar_graficos()

# --- CAJA DE CONFIRMACIÓN (Ocupa todo el ancho por debajo) ---
if st.session_state.confirmando:
    st.divider()
    st.warning("⚠️ **Verifica los datos antes de guardarlos:**")
    
    d = st.session_state.datos_temp
    st.info(f"""
    - **Tipo:** {d['tipo']}
    - **Concepto:** {d['concepto']}
    - **Importe:** {d['importe']} €
    - **Categoría:** {d['nombre_categoria']}
    - **Fecha:** {d['fecha']}
    - **Detalles:** {d['detalles'] if d['detalles'] else 'Ninguno'}
    """)
    
    col_ok, col_ko = st.columns([1, 5])
    
    with col_ok:
        if st.button("Confirmar registro", type="primary"):
            payload = {
                "concepto": d['concepto'],
                "importe": d['importe'],
                "categoria_id": d['categoria_id'],
                "fecha": d['fecha'],
                "detalles": d['detalles']
            }
            try:
                supabase.table("registros").insert(payload).execute()
                st.session_state.confirmando = False
                st.session_state.datos_temp = None
                st.session_state.mensaje_exito = f"✅ {d['tipo']} ({d['concepto']}) registrado correctamente."
                st.session_state.form_key += 1 
                st.rerun()
            except Exception as e:
                st.error(f"Error en la base de datos: {e}")
                
    with col_ko:
        if st.button("Cancelar"):
            st.session_state.confirmando = False
            st.session_state.datos_temp = None
            st.rerun()

# --- TABLA DE HISTORIAL ---
st.divider()
st.subheader("📋 Últimos 5 movimientos")

def mostrar_tabla():
    res = (supabase.table("registros")
           .select("id, fecha, concepto, importe, detalles, categoria_id, categorias(nombre)")
           .order("id", desc=True).limit(5).execute())
    
    if res.data:
        cat_ingresos = supabase.table("categorias").select("id").eq("id_padre", 1).execute()
        ids_ingresos = [c['id'] for c in cat_ingresos.data]

        df = []
        for r in res.data:
            es_ingreso = r['categoria_id'] in ids_ingresos
            signo = "+" if es_ingreso else "-"
            
            df.append({
                "Concepto": r['concepto'],
                "Importe": f"{signo}{r['importe']} €",
                "Fecha": r['fecha'],
                "Categoría": r['categorias']['nombre'],
                "Detalles": r.get('detalles', '')
            })
        
        dataframe = pd.DataFrame(df)
        dataframe.index = range(1, len(dataframe) + 1)
        
        def resaltar_importe(row):
            colores = []
            for col in row.index:
                if col == 'Importe':
                    if '+' in row['Importe']:
                        colores.append('color: #23b854; font-weight: bold;') 
                    else:
                        colores.append('color: #ff4b4b; font-weight: bold;') 
                else:
                    colores.append('') 
            return colores
        
        st.dataframe(dataframe.style.apply(resaltar_importe, axis=1), use_container_width=True)

mostrar_tabla()

# --- ZONA DE PELIGRO (Eliminar) ---
st.divider()
with st.expander("⚠️ Zona de Peligro: Eliminar un registro incorrecto"):
    # Traemos los últimos 10 movimientos por si el error no es el último exacto
    res_del = supabase.table("registros").select("id, concepto, importe, fecha").order("id", desc=True).limit(10).execute()
    
    if res_del.data:
        # Creamos una lista legible para el desplegable
        opciones_borrar = {f"[{r['fecha']}] {r['concepto']} - {r['importe']}€ (ID: {r['id']})": r['id'] for r in res_del.data}
        
        col_del1, col_del2 = st.columns([3, 1])
        with col_del1:
            registro_a_borrar = st.selectbox("Selecciona el movimiento a eliminar:", options=list(opciones_borrar.keys()))
        with col_del2:
            st.write("") # Espaciador para alinear el botón con el desplegable
            st.write("")
            if st.button("🗑️ Eliminar definitivamente"):
                id_borrar = opciones_borrar[registro_a_borrar]
                try:
                    supabase.table("registros").delete().eq("id", id_borrar).execute()
                    st.success("✅ Registro eliminado correctamente.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al eliminar: {e}")
    else:
        st.info("No hay registros recientes para eliminar.")