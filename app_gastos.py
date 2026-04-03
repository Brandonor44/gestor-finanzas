import streamlit as st
from supabase import create_client, Client
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

st.set_page_config(page_title="Finanzas Brandon", page_icon="💰", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("🚀 Sistema de Gestión Financiera - Brandon Edition")

# --- BARRA LATERAL (FILTROS) ---
st.sidebar.header("📅 Filtro de Periodo")
hoy = datetime.date.today()

meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", 
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

mes_sel_nombre = st.sidebar.selectbox("Selecciona el Mes:", meses_nombres, index=hoy.month - 1)
anio_sel = st.sidebar.number_input("Año:", min_value=2024, max_value=2030, value=hoy.year)

mes_idx = meses_nombres.index(mes_sel_nombre) + 1
primer_dia_filtro = datetime.date(anio_sel, mes_idx, 1)
ultimo_dia_filtro = datetime.date(anio_sel, mes_idx, monthrange(anio_sel, mes_idx)[1])

if mes_idx == 1:
    mes_prev = 12
    anio_prev = anio_sel - 1
else:
    mes_prev = mes_idx - 1
    anio_prev = anio_sel
primer_dia_prev = datetime.date(anio_prev, mes_prev, 1)
ultimo_dia_prev = datetime.date(anio_prev, mes_prev, monthrange(anio_prev, mes_prev)[1])

if st.session_state.mensaje_exito:
    st.success(st.session_state.mensaje_exito)
    st.session_state.mensaje_exito = None

# Cargamos TODAS las categorías una vez para hacer la magia de niveles
@st.cache_data(ttl=60)
def obtener_todas_las_categorias():
    res = supabase.table("categorias").select("*").execute()
    return res.data

todas_las_cat = obtener_todas_las_categorias()

def obtener_categorias_input(tipo):
    if tipo == "INGRESO":
        return {c['nombre']: c['id'] for c in todas_las_cat if c.get('id_padre') == 1 and c.get('nivel') == 2}
    else:
        return {c['nombre']: c['id'] for c in todas_las_cat if c.get('nivel') == 4}

# --- RENDERIZADO PRINCIPAL ---
st.divider()

col_izq, col_der = st.columns([1, 1], gap="large")

with col_izq:
    st.subheader("📝 Nuevo Registro")
    tipo_mov = st.radio("Tipo:", ["GASTO", "INGRESO"], horizontal=True)
    cat_dict = obtener_categorias_input(tipo_mov)

    with st.form(f"registro_form_{st.session_state.form_key}", clear_on_submit=False):
        col_a, col_b = st.columns(2)
        with col_a:
            concepto = st.text_input("Concepto", placeholder="Nuevo registro")
            fecha = st.date_input("Fecha")
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
                    "concepto": concepto, "importe": importe, "categoria_id": cat_dict[categoria_sel],
                    "nombre_categoria": categoria_sel, "fecha": str(fecha), "tipo": tipo_mov, 
                    "detalles": detalles, "metodo_pago": metodo
                }
                st.session_state.confirmando = True
                st.rerun()

with col_der:
    st.subheader(f"📊 Resumen de {mes_sel_nombre}")
    
    res_metricas = supabase.table("registros").select("id, fecha, concepto, importe, detalles, metodo_pago, categoria_id, categorias(nombre)").gte("fecha", str(primer_dia_filtro)).lte("fecha", str(ultimo_dia_filtro)).order("fecha", desc=True).order("id", desc=True).execute()
    res_prev = supabase.table("registros").select("importe, categoria_id, categorias(nombre)").gte("fecha", str(primer_dia_prev)).lte("fecha", str(ultimo_dia_prev)).execute()
    
    ids_ingresos = [c['id'] for c in todas_las_cat if c.get('id_padre') == 1]
    
    if res_metricas.data:
        total_ingresos = sum(r['importe'] for r in res_metricas.data if r['categoria_id'] in ids_ingresos)
        total_gastos = sum(r['importe'] for r in res_metricas.data if r['categoria_id'] not in ids_ingresos)
        balance = total_ingresos - total_gastos
        
        max_val = max(total_ingresos, total_gastos) if max(total_ingresos, total_gastos) > 0 else 1 
        
        pct_ingresos = min((total_ingresos / max_val) * 100, 100)
        pct_gastos = min((total_gastos / max_val) * 100, 100)
        pct_balance = min((abs(balance) / max_val) * 100, 100)
        color_balance = "#23b854" if balance >= 0 else "#ff4b4b"

        st.markdown(f"""
        <div style="margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-size: 18px; font-weight: 500;">🟢 Ingresos</span>
                <span style="font-size: 18px; font-weight: bold;">{total_ingresos:,.2f} €</span>
            </div>
            <div style="background-color: rgba(150, 150, 150, 0.2); border-radius: 6px; width: 100%; height: 12px;">
                <div style="background-color: #23b854; width: {pct_ingresos}%; height: 100%; border-radius: 6px;"></div>
            </div>
        </div>
        
        <div style="margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-size: 18px; font-weight: 500;">🔴 Gastos</span>
                <span style="font-size: 18px; font-weight: bold;">{total_gastos:,.2f} €</span>
            </div>
            <div style="background-color: rgba(150, 150, 150, 0.2); border-radius: 6px; width: 100%; height: 12px;">
                <div style="background-color: #ff4b4b; width: {pct_gastos}%; height: 100%; border-radius: 6px;"></div>
            </div>
        </div>
        
        <div style="margin-bottom: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-size: 18px; font-weight: 500;">⚖️ Balance</span>
                <span style="font-size: 18px; font-weight: bold; color: {color_balance};">{balance:,.2f} €</span>
            </div>
            <div style="background-color: rgba(150, 150, 150, 0.2); border-radius: 6px; width: 100%; height: 12px;">
                <div style="background-color: {color_balance}; width: {pct_balance}%; height: 100%; border-radius: 6px;"></div>
            </div>
        </div>
        <hr style="margin: 20px 0; border-color: rgba(150, 150, 150, 0.2);">
        """, unsafe_allow_html=True)

        st.markdown("#### 🔥 Top Fugas de Dinero (Global)")
        
        gastos_agrupados = {}
        for r in res_metricas.data:
            if r['categoria_id'] not in ids_ingresos:
                cat_nombre = r['categorias']['nombre']
                gastos_agrupados[cat_nombre] = gastos_agrupados.get(cat_nombre, 0) + r['importe']
                
        gastos_prev_agrupados = {}
        for r in res_prev.data:
            if r['categoria_id'] not in ids_ingresos:
                cat_nombre = r['categorias']['nombre']
                gastos_prev_agrupados[cat_nombre] = gastos_prev_agrupados.get(cat_nombre, 0) + r['importe']

        if gastos_agrupados:
            top_5 = sorted(gastos_agrupados.items(), key=lambda x: x[1], reverse=True)[:5]
            max_cat_val = top_5[0][1] 
            
            html_top5 = ""
            for cat, importe in top_5:
                importe_prev = gastos_prev_agrupados.get(cat, 0)
                
                if importe_prev == 0:
                    trend_txt, trend_color = "Nuevo", "#ff4b4b" 
                else:
                    dif_pct = ((importe - importe_prev) / importe_prev) * 100
                    trend_txt, trend_color = (f"↑ {dif_pct:.0f}%", "#ff4b4b") if dif_pct > 0 else (f"↓ {abs(dif_pct):.0f}%", "#23b854")
                
                pct_barra = (importe / max_cat_val) * 100
                html_top5 += f"""
                <div style="margin-bottom: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
                        <span style="font-size: 14px; font-weight: 500; color: #E0E0E0;">{cat.title()}</span>
                        <div style="text-align: right;">
                            <span style="font-size: 14px; font-weight: bold; margin-right: 8px;">{importe:,.2f} €</span>
                            <span style="font-size: 12px; font-weight: bold; color: {trend_color}; background-color: {trend_color}20; padding: 2px 6px; border-radius: 4px;">{trend_txt}</span>
                        </div>
                    </div>
                    <div style="background-color: rgba(150, 150, 150, 0.2); border-radius: 4px; width: 100%; height: 6px;">
                        <div style="background-color: #ff4b4b; width: {pct_barra}%; height: 100%; border-radius: 4px; opacity: 0.8;"></div>
                    </div>
                </div>
                """
            st.markdown(html_top5, unsafe_allow_html=True)
    else:
        st.info("No hay registros en este periodo.")

if st.session_state.confirmando:
    st.divider()
    d = st.session_state.datos_temp
    st.warning("⚠️ Revisa los datos antes de guardar:")
    col_ok, col_ko = st.columns([1, 5])
    with col_ok:
        if st.button("Confirmar registro", type="primary"):
            try:
                supabase.table("registros").insert({
                    "concepto": d['concepto'], "importe": d['importe'], "categoria_id": d['categoria_id'], 
                    "fecha": d['fecha'], "detalles": d['detalles'], "metodo_pago": d['metodo_pago']
                }).execute()
                st.session_state.confirmando, st.session_state.datos_temp = False, None
                st.session_state.mensaje_exito = "✅ Registrado correctamente."
                st.session_state.form_key += 1
                st.rerun()
            except Exception as e: st.error(f"Error: {e}")
    with col_ko:
        if st.button("Cancelar"):
            st.session_state.confirmando, st.session_state.datos_temp = False, None
            st.rerun()

# --- NUEVO: AUDITOR DE CATEGORÍAS AVANZADO (Árbol Jerárquico) ---
st.divider()
st.subheader(f"🔍 Auditor de Gastos Avanzado")

# Buscador de hijos para filtrar
def obtener_ids_descendientes(id_padre, categorias_list):
    hijos = [c['id'] for c in categorias_list if c.get('id_padre') == id_padre]
    resultado = [id_padre] 
    for hijo_id in hijos:
        resultado.extend(obtener_ids_descendientes(hijo_id, categorias_list))
    return list(set(resultado))

# NUEVA FUNCIÓN: Trepar por el árbol para agrupar por el hijo inmediato
def obtener_nombre_hijo_directo(id_registro, id_padre_sel, lista_cat):
    if id_registro == id_padre_sel:
        cat = next((c for c in lista_cat if c['id'] == id_registro), None)
        return cat['nombre'] if cat else "Otros"
        
    cat_actual = next((c for c in lista_cat if c['id'] == id_registro), None)
    while cat_actual:
        if cat_actual.get('id_padre') == id_padre_sel:
            return cat_actual['nombre']
        cat_actual = next((c for c in lista_cat if c['id'] == cat_actual.get('id_padre')), None)
    return "Otros"

# Preparamos el desplegable
cat_solo_gastos = [c for c in todas_las_cat if c.get('id') not in ids_ingresos and c.get('id_padre') != 1]
lista_nombres_cat = sorted([c['nombre'] for c in cat_solo_gastos])
lista_opciones_cat = ["Todas"] + lista_nombres_cat

filtro_seleccionado = st.selectbox("Selecciona un bloque (ej. Suministros) o un gasto específico (ej. Luz):", lista_opciones_cat)

ids_a_filtrar = []

if filtro_seleccionado != "Todas":
    cat_seleccionada = next((c for c in todas_las_cat if c['nombre'] == filtro_seleccionado), None)
    id_cat_sel = cat_seleccionada['id']
    
    ids_a_filtrar = obtener_ids_descendientes(id_cat_sel, todas_las_cat)
    
    # Filtramos los registros
    registros_actuales = [r for r in res_metricas.data if r['categoria_id'] in ids_a_filtrar] if res_metricas.data else []
    registros_previos = [r for r in res_prev.data if r['categoria_id'] in ids_a_filtrar] if res_prev.data else []
    
    tot_actual = sum(r['importe'] for r in registros_actuales)
    tot_prev = sum(r['importe'] for r in registros_previos)
    dif_importe = tot_actual - tot_prev
    
    if tot_prev == 0:
        trend_txt, trend_color = "Nuevo", "#ff4b4b" if tot_actual > 0 else "#23b854"
    else:
        dif_pct = ((tot_actual - tot_prev) / tot_prev) * 100
        trend_txt, trend_color = (f"↑ {dif_pct:.0f}%", "#ff4b4b") if dif_pct > 0 else (f"↓ {abs(dif_pct):.0f}%", "#23b854")

    signo_dif = "+" if dif_importe > 0 else ""

    col_audit_izq, col_audit_der = st.columns([1, 1], gap="large")
    
    with col_audit_izq:
        st.markdown(f"##### 📈 Análisis de: **{filtro_seleccionado}**")
        st.markdown(f"""
        <div style="margin-top: 15px; padding: 15px; background-color: rgba(150, 150, 150, 0.05); border-radius: 8px;">
            <p style="font-size: 14px; color: #888; margin-bottom: 2px;">Gasto este mes</p>
            <div style="display: flex; align-items: baseline; gap: 15px; margin-bottom: 5px;">
                <span style="font-size: 32px; font-weight: bold;">{tot_actual:,.2f} €</span>
                <span style="font-size: 16px; font-weight: bold; color: {trend_color}; background-color: {trend_color}20; padding: 4px 8px; border-radius: 6px;">{trend_txt}</span>
            </div>
            <p style="font-size: 15px; font-weight: 500; color: {trend_color}; margin-top: 5px; margin-bottom: 5px;">Diferencia: {signo_dif}{dif_importe:,.2f} €</p>
            <p style="font-size: 14px; color: #888; margin-top: 0; margin-bottom: 0;">Mes anterior: {tot_prev:,.2f} €</p>
        </div>
        """, unsafe_allow_html=True)
            
    with col_audit_der:
        if registros_actuales:
            st.markdown(f"##### 📊 Estructura del Gasto")
            
            # Desglose agrupado por el HIJO INMEDIATO del bloque seleccionado
            desglose = {}
            for r in registros_actuales:
                nom_agrupado = obtener_nombre_hijo_directo(r['categoria_id'], id_cat_sel, todas_las_cat)
                desglose[nom_agrupado] = desglose.get(nom_agrupado, 0) + r['importe']
                
            desglose_prev = {}
            for r in registros_previos:
                nom_agrupado = obtener_nombre_hijo_directo(r['categoria_id'], id_cat_sel, todas_las_cat)
                desglose_prev[nom_agrupado] = desglose_prev.get(nom_agrupado, 0) + r['importe']
            
            desglose_ordenado = sorted(desglose.items(), key=lambda x: x[1], reverse=True)
            es_bloque = len(ids_a_filtrar) > 1 or (len(desglose_ordenado) == 1 and desglose_ordenado[0][0] != filtro_seleccionado)
            
            html_desglose = "<div style='margin-top: 15px;'>"
            
            if es_bloque:
                max_desglose = max(tot_actual, 1) 
                for nom_cat, imp in desglose_ordenado:
                    imp_prev = desglose_prev.get(nom_cat, 0)
                    if imp_prev == 0:
                        t_txt, t_col = "Nuevo", "#ff4b4b"
                    else:
                        d_pct = ((imp - imp_prev) / imp_prev) * 100
                        t_txt, t_col = (f"↑ {d_pct:.0f}%", "#ff4b4b") if d_pct > 0 else (f"↓ {abs(d_pct):.0f}%", "#23b854")

                    pct = (imp / max_desglose) * 100
                    html_desglose += f"<div style='margin-bottom: 8px;'><div style='display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2px;'><span style='font-size: 13px;'>{nom_cat.title()}</span><div style='text-align: right;'><span style='font-size: 13px; font-weight: bold; margin-right: 8px;'>{imp:,.2f} €</span><span style='font-size: 11px; font-weight: bold; color: {t_col}; background-color: {t_col}20; padding: 2px 6px; border-radius: 4px;'>{t_txt}</span></div></div><div style='background-color: rgba(150, 150, 150, 0.2); border-radius: 4px; width: 100%; height: 4px;'><div style='background-color: #3498db; width: {pct}%; height: 100%; border-radius: 4px;'></div></div></div>"
                
                html_desglose += f"<hr style='margin: 10px 0; border-color: rgba(150, 150, 150, 0.2);'><div style='margin-bottom: 8px;'><div style='display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2px;'><span style='font-size: 14px; font-weight: bold; color: #E0E0E0;'>TOTAL {filtro_seleccionado.upper()}</span><div style='text-align: right;'><span style='font-size: 14px; font-weight: bold; margin-right: 8px;'>{tot_actual:,.2f} €</span><span style='font-size: 12px; font-weight: bold; color: {trend_color}; background-color: {trend_color}20; padding: 2px 6px; border-radius: 4px;'>{trend_txt}</span></div></div><div style='background-color: rgba(150, 150, 150, 0.2); border-radius: 4px; width: 100%; height: 6px;'><div style='background-color: #9b59b6; width: 100%; height: 100%; border-radius: 4px;'></div></div></div>"
            else:
                html_desglose += f"<div style='margin-bottom: 8px;'><div style='display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 2px;'><span style='font-size: 14px; font-weight: bold; color: #E0E0E0;'>{filtro_seleccionado.upper()}</span><div style='text-align: right;'><span style='font-size: 14px; font-weight: bold; margin-right: 8px;'>{tot_actual:,.2f} €</span><span style='font-size: 12px; font-weight: bold; color: {trend_color}; background-color: {trend_color}20; padding: 2px 6px; border-radius: 4px;'>{trend_txt}</span></div></div><div style='background-color: rgba(150, 150, 150, 0.2); border-radius: 4px; width: 100%; height: 6px;'><div style='background-color: #3498db; width: 100%; height: 100%; border-radius: 4px;'></div></div></div>"
            
            html_desglose += "</div>"
            st.markdown(html_desglose, unsafe_allow_html=True)
            
        else:
            st.info(f"No hay movimientos de {filtro_seleccionado} este mes.")

st.write("") # Espaciado

# --- TABLA DE HISTORIAL FILTRADA ---
def mostrar_tabla_avanzada(res_data, ids_permitidos, filtro_activo):
    if res_data:
        df_list = []
        for r in res_data:
            # Si el filtro está activo, solo mostramos si el ID está en la lista de permitidos
            if filtro_activo != "Todas" and r['categoria_id'] not in ids_permitidos:
                continue
                
            signo = "+" if r['categoria_id'] in ids_ingresos else "-"
            df_list.append({
                "Concepto": r['concepto'], "Importe": f"{signo}{r['importe']} €",
                "Fecha": r['fecha'], "Categoría": r['categorias']['nombre'],
                "Pago": str(r.get('metodo_pago', 'tarjeta')).capitalize(),
                "Detalles": r.get('detalles', '')
            })
        
        if df_list:
            dataframe = pd.DataFrame(df_list)
            dataframe.index = range(1, len(dataframe) + 1)
            
            def resaltar_importe(row):
                return ['color: #23b854; font-weight: bold;' if col == 'Importe' and '+' in row['Importe']
                        else 'color: #ff4b4b; font-weight: bold;' if col == 'Importe'
                        else '' for col in row.index]
            
            st.dataframe(dataframe.style.apply(resaltar_importe, axis=1), use_container_width=True)
        else:
            st.info("La tabla está vacía para los filtros aplicados.")
    else:
        st.info("No hay registros en la base de datos para este mes.")

# Le pasamos los datos que ya consultó la app arriba para no hacer peticiones dobles a Supabase
mostrar_tabla_avanzada(res_metricas.data, ids_a_filtrar, filtro_seleccionado)

with st.expander("⚠️ Zona de Peligro: Eliminar un registro"):
    res_del = supabase.table("registros").select("id, concepto, importe, fecha").order("id", desc=True).limit(10).execute()
    if res_del.data:
        opciones_borrar = {f"[{r['fecha']}] {r['concepto']} - {r['importe']}€ (ID: {r['id']})": r['id'] for r in res_del.data}
        registro_a_borrar = st.selectbox("Selecciona movimiento:", options=list(opciones_borrar.keys()))
        if st.button("🗑️ Eliminar definitivamente"):
            supabase.table("registros").delete().eq("id", opciones_borrar[registro_a_borrar]).execute()
            st.rerun()
