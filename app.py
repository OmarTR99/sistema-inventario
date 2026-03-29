import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestión TAL-IVAN", page_icon="🚜", layout="wide")
st.title("🚜 Sistema Integral Agro: Inventario y Deudas")

# Conexión a las dos pestañas
conn = st.connection("gsheets", type=GSheetsConnection)
df_inv = conn.read(worksheet="Inventario", ttl=0).dropna(how="all")
df_deudas = conn.read(worksheet="Registro_Deudas", ttl=0).dropna(how="all")

# Menú Lateral
menu = ["Inventario y Finanzas", "Cuentas por Cobrar (Clientes)", "Cuentas por Pagar (Proveedores)", "Registrar Nueva Deuda"]
choice = st.sidebar.radio("Navegación", menu)

st.write("---")

# ---------------- SECCIÓN 1: INVENTARIO (Lo que ya teníamos) ----------------
if choice == "Inventario y Finanzas":
    st.subheader("📦 Estado de Almacén")
    st.dataframe(df_inv, use_container_width=True)

# ---------------- SECCIÓN 2: CLIENTES QUE ME DEBEN ----------------
elif choice == "Cuentas por Cobrar (Clientes)":
    st.subheader("👤 Clientes con Pagos Pendientes")
    # Filtrar solo Clientes
    clientes = df_deudas[df_deudas['Tipo'] == "Cliente"]
    
    if not clientes.empty:
        total_cobrar = pd.to_numeric(clientes['Monto']).sum()
        st.metric("Total por Cobrar", f"${total_cobrar:,.2f}")
        
        # Selector para ver detalles de un cliente específico
        lista_clientes = clientes['Nombre'].unique()
        cliente_sel = st.selectbox("Selecciona un cliente para ver qué productos debe:", lista_clientes)
        
        detalles = clientes[clientes['Nombre'] == cliente_sel]
        st.write(f"### Productos que debe {cliente_sel}:")
        st.table(detalles[['Producto', 'Cantidad', 'Monto']])
    else:
        st.info("No hay deudas de clientes registradas.")

# ---------------- SECCIÓN 3: PROVEEDORES A QUIENES DEBO ----------------
elif choice == "Cuentas por Pagar (Proveedores)":
    st.subheader("🤝 Deudas con Proveedores")
    # Filtrar solo Proveedores
    proveedores = df_deudas[df_deudas['Tipo'] == "Proveedor"]
    
    if not proveedores.empty:
        total_pagar = pd.to_numeric(proveedores['Monto']).sum()
        st.error(f"Total Pendiente de Pago: ${total_pagar:,.2f}")
        
        lista_prov = proveedores['Nombre'].unique()
        prov_sel = st.selectbox("Selecciona un proveedor para ver qué mercancía le debes:", lista_prov)
        
        detalles_p = proveedores[proveedores['Nombre'] == prov_sel]
        st.write(f"### Mercancía pendiente con {prov_sel}:")
        st.table(detalles_p[['Producto', 'Cantidad', 'Monto']])
    else:
        st.success("Estás al día con tus proveedores.")

# ---------------- SECCIÓN 4: REGISTRAR NUEVA DEUDA ----------------
elif choice == "Registrar Nueva Deuda":
    st.subheader("📝 Registrar nueva cuenta pendiente")
    with st.form("form_deuda"):
        tipo = st.selectbox("¿Es un Cliente o un Proveedor?", ["Cliente", "Proveedor"])
        nombre = st.text_input("Nombre de la persona/empresa:")
        # Podemos elegir del inventario qué producto está involucrado
        producto = st.selectbox("Producto involucrado:", df_inv['Nombre'].tolist() if not df_inv.empty else ["No hay productos"])
        col1, col2 = st.columns(2)
        cant = col1.number_input("Cantidad de producto:", min_value=1)
        monto = col2.number_input("Monto total de la deuda ($):", min_value=0.0)
        
        if st.form_submit_button("Guardar Deuda"):
            nueva_deuda = pd.DataFrame({
                "Tipo": [tipo], "Nombre": [nombre], "Producto": [producto],
                "Cantidad": [cant], "Monto": [monto]
            })
            df_final_deudas = pd.concat([df_deudas, nueva_deuda], ignore_index=True)
            conn.update(worksheet="Registro_Deudas", data=df_final_deudas)
            st.success("Deuda registrada exitosamente.")
