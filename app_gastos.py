import streamlit as st
from supabase import create_client, Client
import plotly.express as px
import pandas as pd
import datetime
from calendar import monthrange, month_name

# --- INICIALIZAR MEMORIA TEMPORAL ---
if 'confirmando' not in st.session_state:
    st.session_state.confirmando = False
if 'datos_temp' not in st.session_state:
    st.session_state.datos_temp = None
if 'mensaje_exito' not in st.session_state:
    st.session_state.mensaje_exito = None
if 'form_key' not in st.session_state:
    st.session_state.form_key = 0

st.set_page_config(page_title="Finanzas Brandon", page_icon="💰", layout="wide")

# Conexión Segura vía Secrets
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("🚀 Sistema de Gestión Financiera - Brandon Edition")

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("📅 Filtro de Periodo")
hoy = datetime.date.today()

# Creamos una lista de meses en español para el selector
meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

mes_sel_nombre = st.sidebar.selectbox("Selecciona el Mes:", meses_nombres, index=hoy.month - 1)
anio_sel = st.sidebar.number_input("Año:", min_value=2024, max_value=2030, value=hoy.year)

# Convertimos el nombre del mes a número (Enero -> 1)
mes_idx = meses_nombres.index(mes_sel_nombre) + 1

# Calculamos rango de fechas para el filtro SQL
primer_dia_filtro = datetime.date(anio_sel, mes_idx, 1)
ultimo_dia_filtro = datetime.date(anio_sel, mes_idx, monthrange(anio_sel, mes_idx)[1])

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

def mostrar_metricas(f_inicio, f_fin):
    res = supabase.table("registros").select("importe, categoria_id").gte("fecha", str(f_inicio)).lte("fecha", str(f_fin)).execute()
    
    cat_ingresos = supabase.table("categorias").select("id").eq("id_padre", 1).execute()
    ids_ingresos = [c['id'] for c in cat_ingresos.data]
    
    total_ingresos = sum(r['importe'] for r in res.data if r['categoria_id'] in ids_ingresos)
    total_gastos = sum(r['importe'] for r in res.data if r['categoria_id'] not in ids_ingresos)
    balance = total_ingresos - total_gastos
    
    col1, col2, col3 = st.columns(3)
    col1.metric(f"🟢 Ingresos ({mes_sel_nombre})", f"{total_ingresos:,.2f} €")
    col2.metric(f"🔴 Gastos ({mes_sel_nombre})", f"{total_gastos:,.2f} €")
    col3.metric("⚖️ Resultado Neto", f"{balance:,.2f} €")

def mostrar_graficos(f_inicio, f_fin):
    res = (supabase.table("registros")
           .select("importe, categoria_id, categorias(nombre)")
           .gte("fecha", str(f_inicio)).lte("fecha", str(f_fin))
           .execute())
    
    if res.data:
        cat_ingresos = supabase.table("categorias").select("id").eq("id_padre", 1).execute()
        ids_ingresos = [c['id'] for c in cat_ingresos.data]
        
        gastos_data = [{"Categoría": r['categorias']['nombre'], "Importe": r['importe']} 
                       for r in res.data if r['categoria_id'] not in ids_ingresos]
        
        if gastos_data:
            df_resumen = pd.DataFrame(gastos_data).groupby("Categoría")["Importe"].sum().reset_index()
            fig = px.pie(df_resumen, values='Importe', names='Categoría', hole=0.5,
                         title=f"📊 Gastos de {mes_sel_nombre}",
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            fig.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"No hay gastos registrados en {mes_sel_nombre}.")

# --- RENDERIZADO PRINCIPAL ---
mostrar_metricas(primer_dia_filtro, ultimo_dia_filtro)
st.divider()

col_izq, col_der = st.columns([1, 1], gap="large")

with col_izq:
    st.subheader("📝 Nuevo Registro")
    tipo_mov = st.radio("Tipo:", ["GASTO", "INGRESO"], horizontal=True)
    cat_dict = obtener_categorias(tipo_mov)

    with st.form(f"registro_form_{st.session_state.form_key}", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        with col_a:
            concepto = st.text_input("Concepto", placeholder="nuevo registro")
            fecha = st.date_input("Fecha")
            # <--- ¡NUEVO! Selector de pago añadido en la columna izquierda
            metodo = st.selectbox("Método de pago", options=["tarjeta", "efectivo"], index=0) 
            
        with col_b:
            importe = st.number_input("Importe (€)", min_value=0.01, step=0.1, value=None, placeholder="0,00")
            categoria_sel = st.selectbox("Categoría", options=list(cat_dict.keys()))
            detalles = st.text_input("Detalles (Opcional)")
            
        submit = st.form_submit_button("Registrar")

        if submit:
            if importe is None or not concepto:
                st.error("⚠️ Datos incompletos.")
            else:
                st.session_state.datos_temp = {
                    "concepto": concepto, 
                    "importe": importe, 
                    "categoria_id": cat_dict[categoria_sel],
                    "nombre_categoria": categoria_sel, 
                    "fecha": str(fecha), 
                    "tipo": tipo_mov, 
                    "detalles": detalles,
                    "metodo_pago": metodo # <--- ¡NUEVO! Guardamos el método seleccionado
                }
                st.session_state.confirmando = True
                st.rerun()

with col_der:
    mostrar_graficos(primer_dia_filtro, ultimo_dia_filtro)

if st.session_state.confirmando:
    st.divider()
    d = st.session_state.datos_temp
    # <--- ¡NUEVO! Añadido el método de pago al aviso de confirmación
    st.warning(f"⚠️ Confirmar: {d['tipo']} - {d['concepto']} ({d['importe']}€) pagado en {d['metodo_pago'].upper()}")
    
    col_ok, col_ko = st.columns([1, 5])
    with col_ok:
        if st.button("Confirmar registro", type="primary"):
            try:
                supabase.table("registros").insert({
                    "concepto": d['concepto'], 
                    "importe": d['importe'], 
                    "categoria_id": d['categoria_id'], 
                    "fecha": d['fecha'], 
                    "detalles": d['detalles'],
                    "metodo_pago": d['metodo_pago'] # <--- ¡NUEVO! Lo inyectamos en Supabase
                }).execute()
                
                st.session_state.confirmando, st.session_state.datos_temp = False, None
                st.session_state.mensaje_exito = "✅ Registrado correctamente."
                st.session_state.form_key += 1
                st.rerun()
            except Exception as e: 
                st.error(f"Error: {e}")
    with col_ko:
        if st.button("Cancelar"):
            st.session_state.confirmando, st.session_state.datos_temp = False, None
            st.rerun()

# --- TABLA DE HISTORIAL (Filtrada por mes seleccionado) ---
st.divider()
st.subheader(f"📋 Movimientos de {mes_sel_nombre}")

def mostrar_tabla(f_inicio, f_fin):
    # <--- ¡NUEVO! Añadimos metodo_pago a la consulta select de SQL
    res = (supabase.table("registros")
           .select("id, fecha, concepto, importe, detalles, metodo_pago, categoria_id, categorias(nombre)") 
           .gte("fecha", str(f_inicio)).lte("fecha", str(f_fin))
           .order("id", desc=True).execute())
    
    if res.data:
        cat_ingresos = supabase.table("categorias").select("id").eq("id_padre", 1).execute()
        ids_ingresos = [c['id'] for c in cat_ingresos.data]

        df_list = []
        for r in res.data:
            signo = "+" if r['categoria_id'] in ids_ingresos else "-"
            df_list.append({
                "Concepto": r['concepto'], 
                "Importe": f"{signo}{r['importe']} €",
                "Fecha": r['fecha'], 
                "Categoría": r['categorias']['nombre'],
                "Pago": str(r.get('metodo_pago', 'tarjeta')).capitalize(), # <--- ¡NUEVO! Columna en la tabla
                "Detalles": r.get('detalles', '')
            })
        
        dataframe = pd.DataFrame(df_list)
        dataframe.index = range(1, len(dataframe) + 1)
        
        def resaltar_importe(row):
            return ['color: #23b854; font-weight: bold;' if col == 'Importe' and '+' in row['Importe']
                    else 'color: #ff4b4b; font-weight: bold;' if col == 'Importe'
                    else '' for col in row.index]
        
        st.dataframe(dataframe.style.apply(resaltar_importe, axis=1), use_container_width=True)

mostrar_tabla(primer_dia_filtro, ultimo_dia_filtro)

# --- ZONA DE PELIGRO ---
with st.expander("⚠️ Zona de Revisión: Eliminar un registro"):
    res_del = supabase.table("registros").select("id, concepto, importe, fecha").order("id", desc=True).limit(10).execute()
    if res_del.data:
        opciones_borrar = {f"[{r['fecha']}] {r['concepto']} - {r['importe']}€ (ID: {r['id']})": r['id'] for r in res_del.data}
        registro_a_borrar = st.selectbox("Selecciona movimiento:", options=list(opciones_borrar.keys()))
        if st.button("🗑️ Eliminar definitivamente"):
            supabase.table("registros").delete().eq("id", opciones_borrar[registro_a_borrar]).execute()
            st.rerun()
