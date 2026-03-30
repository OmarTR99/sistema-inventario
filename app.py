import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="Gestión Agro Total", page_icon="🚜", layout="wide")
st.title("🚜 Sistema Integral: Inventario, Deudas e Historial")

# 1. Conectar a las 3 pestañas
conn = st.connection("gsheets", type=GSheetsConnection)

# Carga de datos con manejo de errores
try:
    df_inv = conn.read(worksheet="Inventario", ttl=0).dropna(how="all")
    df_deudas = conn.read(worksheet="Registro_Deudas", ttl=0).dropna(how="all")
    df_historial = conn.read(worksheet="Historial", ttl=0).dropna(how="all")
except:
    st.error("Error leyendo las pestañas. Revisa que existan: Inventario, Registro_Deudas e Historial.")
    st.stop()

# Asegurar que las columnas de deudas sean texto para evitar el error .str
if not df_deudas.empty:
    df_deudas['Tipo'] = df_deudas['Tipo'].astype(str)
    df_deudas['Nombre'] = df_deudas['Nombre'].astype(str)

# Menú Lateral
menu = [
    "1. Resumen de Inventario", 
    "2. Registrar Producto Nuevo", 
    "3. Movimiento al Contado", 
    "4. Registrar Deuda (Crédito)", 
    "5. Clientes (Por Cobrar)", 
    "6. Proveedores (Por Pagar)",
    "7. 📜 Historial Completo"
]
choice = st.sidebar.radio("Menú Principal", menu)
st.write("---")

# Función para registrar historial
def registrar_historial(tipo, prod, cant, monto, ganancia):
    global df_historial
    nueva_fila = pd.DataFrame({
        "Fecha": [datetime.now().strftime("%d/%m/%Y %H:%M")],
        "Tipo_Mov": [tipo], "Producto": [prod], "Cantidad": [cant],
        "Monto_Total": [monto], "Ganancia_Real": [ganancia]
    })
    df_h_act = pd.concat([df_historial, nueva_fila], ignore_index=True)
    conn.update(worksheet="Historial", data=df_h_act)

# ---------------- SECCIONES ----------------
if choice == "1. Resumen de Inventario":
    st.subheader("📈 Estado del Almacén")
    if not df_inv.empty:
        st.dataframe(df_inv, use_container_width=True)
    else: st.info("Inventario vacío.")

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
            st.success("Guardado.")

elif choice == "3. Movimiento al Contado":
    st.subheader("🔄 Compra/Venta Instantánea")
    if not df_inv.empty:
        prod = st.selectbox("Seleccione:", df_inv['Nombre'].tolist())
        tipo = st.radio("Acción:", ("Venta", "Compra"))
        cant = st.number_input("Cantidad:", min_value=1)
        if st.button("Procesar"):
            idx = df_inv.index[df_inv['Nombre'] == prod].tolist()[0]
            val = df_inv.at[idx, 'Precio_Venta'] if tipo == "Venta" else df_inv.at[idx, 'Costo_Compra']
            gan = (df_inv.at[idx, 'Ganancia_Unitaria'] * cant) if tipo == "Venta" else 0
            df_inv.at[idx, 'Cantidad'] += (-cant if tipo == "Venta" else cant)
            df_inv.at[idx, 'Ganancia_Total'] = df_inv.at[idx, 'Cantidad'] * df_inv.at[idx, 'Ganancia_Unitaria']
            conn.update(worksheet="Inventario", data=df_inv)
            registrar_historial(tipo, prod, cant, cant*val, gan)
            st.success("¡Listo!")

elif choice == "4. Registrar Deuda (Crédito)":
    st.subheader("📝 Fiao y descarga automática")
    if not df_inv.empty:
        t_d = st.selectbox("Tipo:", ["Cliente", "Proveedor"])
        nom_p = st.text_input("Nombre:")
        prod = st.selectbox("Producto:", df_inv['Nombre'].tolist())
        idx = df_inv.index[df_inv['Nombre'] == prod].tolist()[0]
        precio = df_inv.at[idx, 'Precio_Venta'] if t_d == "Cliente" else df_inv.at[idx, 'Costo_Compra']
        cant = st.number_input("Cantidad:", min_value=1)
        monto = cant * precio
        st.info(f"Monto: ${monto:,.2f}")
        if st.button("Guardar Deuda"):
            # Actualizar Deudas
            n_d = pd.DataFrame({"Tipo":[t_d],"Nombre":[nom_p],"Producto":[prod],"Cantidad":[cant],"Monto":[monto]})
            df_deudas = pd.concat([df_deudas, n_d], ignore_index=True)
            conn.update(worksheet="Registro_Deudas", data=df_deudas)
            # Actualizar Inventario
            df_inv.at[idx, 'Cantidad'] += (-cant if t_d == "Cliente" else cant)
            df_inv.at[idx, 'Ganancia_Total'] = df_inv.at[idx, 'Cantidad'] * df_inv.at[idx, 'Ganancia_Unitaria']
            conn.update(worksheet="Inventario", data=df_inv)
            # Historial
            registrar_historial(f"Deuda {t_d}", prod, cant, monto, (cant*df_inv.at[idx, 'Ganancia_Unitaria'] if t_d == "Cliente" else 0))
            st.success("Registrado.")

elif choice in ["5. Clientes (Por Cobrar)", "6. Proveedores (Por Pagar)"]:
    tipo_buscado = "Cliente" if "5." in choice else "Proveedor"
    st.subheader(f"👥 Gestión de {tipo_buscado}s")
    sub_df = df_deudas[df_deudas['Tipo'] == tipo_buscado]
    if not sub_df.empty:
        per = st.selectbox("Selecciona Persona:", sub_df['Nombre'].unique())
        st.table(sub_df[sub_df['Nombre'] == per])
        if st.button(f"🗑️ Liquidar deuda de {per}"):
            df_deudas = df_deudas[~(df_deudas['Nombre'] == per)]
            conn.update(worksheet="Registro_Deudas", data=df_deudas)
            st.success("Borrado.")
            st.rerun()
    else: st.info("No hay registros.")

elif "7." in choice:
    st.subheader("📜 Historial")
    st.dataframe(df_historial, use_container_width=True)
