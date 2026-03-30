import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="Gestión Agro Total", page_icon="🚜", layout="wide")
st.title("🚜 Sistema Integral: Inventario, Deudas e Historial")

# 1. Conectar a las 3 pestañas
conn = st.connection("gsheets", type=GSheetsConnection)
df_inv = conn.read(worksheet="Inventario", ttl=0).dropna(how="all")
df_deudas = conn.read(worksheet="Registro_Deudas", ttl=0).dropna(how="all")
df_historial = conn.read(worksheet="Historial", ttl=0).dropna(how="all")

# Asegurar columnas numéricas
for col in ['Cantidad', 'Costo_Compra', 'Precio_Venta', 'Ganancia_Unitaria', 'Ganancia_Total']:
    if col in df_inv.columns:
        df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# Menú Lateral
menu = [
    "1. Resumen de Inventario", 
    "2. Registrar Producto Nuevo", 
    "3. Movimiento al Contado", 
    "4. Registrar Deuda (Crédito)", 
    "5. Clientes y Proveedores",
    "6. 📜 HISTORIAL DE VENTAS Y ENTRADAS"
]
choice = st.sidebar.radio("Menú Principal", menu)
st.write("---")

# Función para registrar en el historial
def registrar_historial(tipo, prod, cant, monto, ganancia):
    global df_historial
    nueva_fila = pd.DataFrame({
        "Fecha": [datetime.now().strftime("%d/%m/%Y %H:%M")],
        "Tipo_Mov": [tipo],
        "Producto": [prod],
        "Cantidad": [cant],
        "Monto_Total": [monto],
        "Ganancia_Real": [ganancia]
    })
    df_historial = pd.concat([df_historial, nueva_fila], ignore_index=True)
    conn.update(worksheet="Historial", data=df_historial)

# ---------------- 1. RESUMEN ----------------
if choice == "1. Resumen de Inventario":
    st.subheader("📈 Estado del Almacén")
    if not df_inv.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Inversión en Stock", f"${(df_inv['Cantidad'] * df_inv['Costo_Compra']).sum():,.2f}")
        c2.metric("Ganancia Proyectada", f"${df_inv['Ganancia_Total'].sum():,.2f}")
        c3.metric("Productos Bajos", len(df_inv[df_inv['Cantidad'] <= df_inv['Stock_Minimo']]))
        st.dataframe(df_inv, use_container_width=True)

# ---------------- 2. PRODUCTO NUEVO ----------------
elif choice == "2. Registrar Producto Nuevo":
    st.subheader("➕ Nuevo Producto")
    with st.form("p_nuevo"):
        nom = st.text_input("Nombre:")
        cat = st.selectbox("Categoría:", ["Agroquímico", "Fertilizante", "Semilla", "Herramienta"])
        c1, c2, c3, c4 = st.columns(4)
        cant = c1.number_input("Stock:", min_value=0)
        s_min = c2.number_input("Mínimo:", min_value=1)
        costo = c3.number_input("Costo:", min_value=0.0)
        venta = c4.number_input("Venta:", min_value=0.0)
        if st.form_submit_button("Guardar"):
            g_u = venta - costo
            n_f = pd.DataFrame({"Nombre":[nom],"Categoria":[cat],"Cantidad":[cant],"Stock_Minimo":[s_min],"Costo_Compra":[costo],"Precio_Venta":[venta],"Ganancia_Unitaria":[g_u],"Ganancia_Total":[cant*g_u]})
            df_inv = pd.concat([df_inv, n_f], ignore_index=True)
            conn.update(worksheet="Inventario", data=df_inv)
            registrar_historial("Carga Inicial", nom, cant, cant*costo, 0)
            st.success("Producto creado e historial registrado.")

# ---------------- 3. CONTADO ----------------
elif choice == "3. Movimiento al Contado":
    st.subheader("🔄 Compra/Venta Instantánea")
    if not df_inv.empty:
        prod = st.selectbox("Seleccione:", df_inv['Nombre'].tolist())
        tipo = st.radio("Acción:", ("Venta (Resta)", "Compra (Suma)"))
        cant = st.number_input("Cantidad:", min_value=1)
        if st.button("Procesar"):
            idx = df_inv.index[df_inv['Nombre'] == prod].tolist()[0]
            val_u = df_inv.at[idx, 'Precio_Venta'] if "Venta" in tipo else df_inv.at[idx, 'Costo_Compra']
            gan_u = df_inv.at[idx, 'Ganancia_Unitaria'] if "Venta" in tipo else 0
            
            n_stock = df_inv.at[idx, 'Cantidad'] + (cant if "Compra" in tipo else -cant)
            if n_stock < 0: st.error("Sin stock")
            else:
                df_inv.at[idx, 'Cantidad'] = n_stock
                df_inv.at[idx, 'Ganancia_Total'] = n_stock * df_inv.at[idx, 'Ganancia_Unitaria']
                conn.update(worksheet="Inventario", data=df_inv)
                registrar_historial(tipo, prod, cant, cant*val_u, cant*gan_u)
                st.success("¡Hecho! Guardado en historial.")
                st.rerun()

# ---------------- 4. DEUDAS ----------------
elif choice == "4. Registrar Deuda (Crédito)":
    st.subheader("📝 Fiao con descarga de stock")
    if not df_inv.empty:
        t_d = st.selectbox("Tipo:", ["Cliente", "Proveedor"])
        nom_p = st.text_input("Nombre Persona:")
        prod = st.selectbox("Producto:", df_inv['Nombre'].tolist())
        idx = df_inv.index[df_inv['Nombre'] == prod].tolist()[0]
        p_u = df_inv.at[idx, 'Precio_Venta'] if t_d == "Cliente" else df_inv.at[idx, 'Costo_Compra']
        cant = st.number_input("Cantidad:", min_value=1)
        monto = cant * p_u
        st.info(f"Total: ${monto:,.2f}")
        if st.button("Guardar Deuda"):
            if t_d == "Cliente" and df_inv.at[idx, 'Cantidad'] < cant: st.error("Sin stock")
            else:
                # Actualizar Deudas
                n_d = pd.DataFrame({"Tipo":[t_d],"Nombre":[nom_p],"Producto":[prod],"Cantidad":[cant],"Monto":[monto]})
                df_deudas = pd.concat([df_deudas, n_d], ignore_index=True)
                conn.update(worksheet="Registro_Deudas", data=df_deudas)
                # Actualizar Stock
                df_inv.at[idx, 'Cantidad'] += (-cant if t_d == "Cliente" else cant)
                df_inv.at[idx, 'Ganancia_Total'] = df_inv.at[idx, 'Cantidad'] * df_inv.at[idx, 'Ganancia_Unitaria']
                conn.update(worksheet="Inventario", data=df_inv)
                # Historial
                registrar_historial(f"Deuda {t_d}", prod, cant, monto, (cant*df_inv.at[idx, 'Ganancia_Unitaria'] if t_d == "Cliente" else 0))
                st.success("Deuda e Historial registrados.")

# ---------------- 5. LIQUIDAR ----------------
elif "5." in choice:
    st.subheader("👥 Gestión de Cuentas")
    t_v = "Cliente" if "Clientes" in choice else "Proveedor"
    sub_df = df_deudas[df_deudas['Tipo'].str.contains(t_v, na=False)]
    if not sub_df.empty:
        per = st.selectbox("Persona:", sub_df['Nombre'].unique())
        st.table(sub_df[sub_df['Nombre'] == per])
        if st.button(f"Borrar deuda de {per}"):
            df_deudas = df_deudas[~(df_deudas['Nombre'] == per)]
            conn.update(worksheet="Registro_Deudas", data=df_deudas)
            st.success("Cuenta borrada.")
            st.rerun()
    else: st.info("Sin registros.")

# ---------------- 6. HISTORIAL ----------------
elif "6." in choice:
    st.subheader("📜 Historial Completo de Movimientos")
    if not df_historial.empty:
        # Métricas de rendimiento
        c1, c2 = st.columns(2)
        total_v = pd.to_numeric(df_historial[df_historial['Tipo_Mov'].str.contains("Venta|Cliente", na=False)]['Monto_Total']).sum()
        total_g = pd.to_numeric(df_historial['Ganancia_Real']).sum()
        c1.metric("Ventas Totales (Acumulado)", f"${total_v:,.2f}")
        c2.metric("Ganancia Real (Acumulado)", f"${total_g:,.2f}", delta="Dinero neto")
        
        st.write("### Lista de transacciones")
        st.dataframe(df_historial.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("El historial está vacío.")
