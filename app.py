import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime, timedelta

st.set_page_config(page_title="Gestión Agro", page_icon="🚜", layout="wide")
st.title("🚜 Control TAL-IVAN: Inventario y Cuentas")

# 1. Conexión Protegida
conn = st.connection("gsheets", type=GSheetsConnection)

def cargar_datos(pestaña):
    try:
        return conn.read(worksheet=pestaña, ttl=0).dropna(how="all")
    except:
        return pd.DataFrame()

df_inv = cargar_datos("Inventario")
df_deudas = cargar_datos("Registro_Deudas")
df_historial = cargar_datos("Historial")

# Función blindada para guardar el historial sin romper la página
def guardar_historial(tipo, producto, cantidad, monto, ganancia=0):
    try:
        # Ajuste a hora de Venezuela (UTC-4)
        hora_local = datetime.utcnow() - timedelta(hours=4)
        fecha_str = hora_local.strftime("%d/%m/%Y %I:%M %p")
        
        nuevo_reg = pd.DataFrame({
            "Fecha": [fecha_str], 
            "Tipo_Mov": [tipo], 
            "Producto": [producto], 
            "Cantidad": [cantidad], 
            "Monto_Total": [monto],
            "Ganancia_Real": [ganancia]
        })
        global df_historial
        df_historial = pd.concat([df_historial, nuevo_reg], ignore_index=True)
        conn.update(worksheet="Historial", data=df_historial)
    except:
        pass # Si falla la hoja, el sistema ignora el error y sigue trabajando

# 2. Menú Lateral
menu = [
    "📊 Resumen General", 
    "➕ Nuevo Producto", 
    "🛒 Venta/Compra Contado", 
    "💳 Registrar Deuda (Fiao)", 
    "👥 Gestionar Deudas (Pagar/Cobrar)",
    "📜 Historial de Movimientos"
]
choice = st.sidebar.radio("Menú", menu)
st.write("---")

# ---------------- SECCIONES ----------------

if choice == "📊 Resumen General":
    st.subheader("Estado Actual")
    if not df_inv.empty:
        st.dataframe(df_inv, use_container_width=True)
    else: st.info("El inventario está vacío.")

elif choice == "➕ Nuevo Producto":
    st.subheader("Registrar Producto en Catálogo")
    with st.form("f1"):
        nom = st.text_input("Nombre:")
        cat = st.selectbox("Tipo:", ["Agroquímico", "Fertilizante", "Semilla"])
        c1, c2 = st.columns(2)
        stock = c1.number_input("Cantidad inicial:", min_value=0)
        s_min = c2.number_input("Alerta mínimo:", min_value=1)
        c3, c4 = st.columns(2)
        costo = c3.number_input("Costo compra ($):", min_value=0.0)
        venta = c4.number_input("Precio venta ($):", min_value=0.0)
        
        if st.form_submit_button("Guardar Producto"):
            gan_u = venta - costo
            nueva_f = pd.DataFrame({"Nombre":[nom], "Categoria":[cat], "Cantidad":[stock], "Stock_Minimo":[s_min], "Costo_Compra":[costo], "Precio_Venta":[venta], "Ganancia_Unitaria":[gan_u], "Ganancia_Total":[stock*gan_u]})
            df_inv = pd.concat([df_inv, nueva_f], ignore_index=True)
            conn.update(worksheet="Inventario", data=df_inv)
            
            # Guardar en historial
            guardar_historial("Inventario Inicial", nom, stock, stock*costo, 0)
            st.success("✅ Producto guardado correctamente.")

elif choice == "🛒 Venta/Compra Contado":
    st.subheader("Movimiento de Mercancía")
    if not df_inv.empty:
        p_sel = st.selectbox("Producto:", df_inv['Nombre'].tolist())
        tipo = st.radio("Acción:", ["Venta", "Compra"])
        cant = st.number_input("Cantidad:", min_value=1)
        if st.button("Procesar"):
            idx = df_inv.index[df_inv['Nombre'] == p_sel].tolist()[0]
            
            # Cálculos de dinero para el historial
            precio_u = df_inv.at[idx, 'Precio_Venta'] if tipo == "Venta" else df_inv.at[idx, 'Costo_Compra']
            gan_u = df_inv.at[idx, 'Ganancia_Unitaria'] if tipo == "Venta" else 0
            
            # Actualizar stock
            df_inv.at[idx, 'Cantidad'] += (-cant if tipo == "Venta" else cant)
            df_inv.at[idx, 'Ganancia_Total'] = df_inv.at[idx, 'Cantidad'] * df_inv.at[idx, 'Ganancia_Unitaria']
            conn.update(worksheet="Inventario", data=df_inv)
            
            # Guardar en historial
            guardar_historial(f"{tipo} Contado", p_sel, cant, cant*precio_u, cant*gan_u)
            st.success("✅ Inventario actualizado.")
    else: st.warning("Crea productos primero.")

elif choice == "💳 Registrar Deuda (Fiao)":
    st.subheader("Registrar Cuenta Pendiente")
    if not df_inv.empty:
        t_d = st.selectbox("Tipo:", ["Cliente (Me debe)", "Proveedor (Le debo)"])
        p_nombre = st.text_input("Nombre de la persona:")
        p_prod = st.selectbox("Producto:", df_inv['Nombre'].tolist())
        cant = st.number_input("Cantidad:", min_value=1)
        
        idx = df_inv.index[df_inv['Nombre'] == p_prod].tolist()[0]
        precio = df_inv.at[idx, 'Precio_Venta'] if "Cliente" in t_d else df_inv.at[idx, 'Costo_Compra']
        monto = cant * precio
        st.write(f"### Total Deuda: ${monto:,.2f}")
        
        if st.button("Guardar Deuda"):
            t_real = "Cliente" if "Cliente" in t_d else "Proveedor"
            
            # 1. Guardar la deuda
            n_deuda = pd.DataFrame({"Tipo":[t_real], "Nombre":[p_nombre], "Producto":[p_prod], "Cantidad":[cant], "Monto":[monto]})
            df_deudas = pd.concat([df_deudas, n_deuda], ignore_index=True)
            conn.update(worksheet="Registro_Deudas", data=df_deudas)
            
            # 2. Descontar stock
            df_inv.at[idx, 'Cantidad'] += (-cant if t_real == "Cliente" else cant)
            df_inv.at[idx, 'Ganancia_Total'] = df_inv.at[idx, 'Cantidad'] * df_inv.at[idx, 'Ganancia_Unitaria']
            conn.update(worksheet="Inventario", data=df_inv)
            
            # 3. Guardar en historial
            gan_historial = cant * df_inv.at[idx, 'Ganancia_Unitaria'] if t_real == "Cliente" else 0
            guardar_historial(f"Fiao a {t_real}", p_prod, cant, monto, gan_historial)
            
            st.success("✅ Deuda registrada y stock actualizado.")
    else: st.warning("Sin productos.")

elif choice == "👥 Gestionar Deudas (Pagar/Cobrar)":
    st.subheader("Cobros y Pagos")
    if not df_deudas.empty:
        tipo = st.radio("Ver:", ["Clientes", "Proveedores"])
        t_b = "Cliente" if tipo == "Clientes" else "Proveedor"
        resumen = df_deudas[df_deudas['Tipo'] == t_b]
        
        if not resumen.empty:
            persona = st.selectbox("Selecciona nombre:", resumen['Nombre'].unique())
            st.table(resumen[resumen['Nombre'] == persona])
            if st.button(f"🗑️ Liquidar Deuda de {persona}"):
                df_deudas = df_deudas[df_deudas['Nombre'] != persona]
                conn.update(worksheet="Registro_Deudas", data=df_deudas)
                
                guardar_historial(f"Cuenta de {t_b} liquidada", persona, 1, 0, 0)
                st.success("Cuenta borrada.")
                st.rerun()
        else: st.info("No hay deudas en esta categoría.")
    else: st.info("No hay deudas registradas.")

elif choice == "📜 Historial de Movimientos":
    st.subheader("Registro Total de Operaciones")
    if not df_historial.empty:
        st.dataframe(df_historial.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("Aún no hay movimientos registrados.")
