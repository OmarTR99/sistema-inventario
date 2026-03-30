import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestión Agro-Integral", page_icon="🚜", layout="wide")
st.title("🚜 Sistema Integral Agro: Inventario, Finanzas y Deudas")

# Conectar a las dos pestañas
conn = st.connection("gsheets", type=GSheetsConnection)
df_inv = conn.read(worksheet="Inventario", ttl=0).dropna(how="all")
df_deudas = conn.read(worksheet="Registro_Deudas", ttl=0).dropna(how="all")

# Convertir columnas a números
cols_num = ['Cantidad', 'Stock_Minimo', 'Costo_Compra', 'Precio_Venta', 'Ganancia_Unitaria', 'Ganancia_Total']
for col in cols_num:
    if col in df_inv.columns:
        df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# Menú Lateral
st.sidebar.title("Menú Principal")
menu = [
    "Resumen de Inventario", 
    "Entradas y Salidas", 
    "Registrar Producto Nuevo", 
    "Cuentas por Cobrar (Clientes)", 
    "Cuentas por Pagar (Proveedores)", 
    "Registrar Nueva Deuda"
]
choice = st.sidebar.radio("Navegación", menu)

st.write("---")

# ---------------- 1. RESUMEN DE INVENTARIO ----------------
if choice == "Resumen de Inventario":
    st.subheader("📈 Estado del Almacén y Finanzas")
    if not df_inv.empty:
        inversion = (df_inv['Cantidad'] * df_inv['Costo_Compra']).sum()
        ganancia = df_inv['Ganancia_Total'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Inversión en Almacén", f"${inversion:,.2f}")
        c2.metric("Ganancia Esperada", f"${ganancia:,.2f}")
        c3.metric("Alertas de Stock", len(df_inv[df_inv['Cantidad'] <= df_inv['Stock_Minimo']]))
        
        st.dataframe(df_inv[['Nombre', 'Categoria', 'Cantidad', 'Costo_Compra', 'Precio_Venta', 'Ganancia_Unitaria', 'Ganancia_Total']], use_container_width=True)
    else:
        st.info("No hay productos en el inventario.")

# ---------------- 2. ENTRADAS Y SALIDAS ----------------
elif choice == "Entradas y Salidas":
    st.subheader("🔄 Registrar Movimiento (Contado)")
    if not df_inv.empty:
        prod = st.selectbox("Producto:", df_inv['Nombre'].tolist())
        tipo = st.radio("Acción:", ("Entrada", "Salida (Venta)"))
        cant_mov = st.number_input("Cantidad:", min_value=1, step=1)
        
        if st.button("Procesar"):
            idx = df_inv.index[df_inv['Nombre'] == prod].tolist()[0]
            stock_actual = df_inv.at[idx, 'Cantidad']
            
            nuevo_stock = stock_actual + cant_mov if tipo == "Entrada" else stock_actual - cant_mov
                
            if nuevo_stock < 0:
                st.error("No hay suficiente stock.")
            else:
                df_inv.at[idx, 'Cantidad'] = nuevo_stock
                df_inv.at[idx, 'Ganancia_Total'] = nuevo_stock * df_inv.at[idx, 'Ganancia_Unitaria']
                conn.update(worksheet="Inventario", data=df_inv)
                st.success(f"Stock actualizado. Nuevo Total: {nuevo_stock}")
                st.rerun()

# ---------------- 3. REGISTRAR PRODUCTO NUEVO ----------------
elif choice == "Registrar Producto Nuevo":
    st.subheader("➕ Agregar Producto al Catálogo")
    with st.form("nuevo_p"):
        nombre = st.text_input("Nombre del Producto:")
        cat = st.selectbox("Categoría:", ["Fertilizante", "Semilla", "Agroquímico", "Herramienta"])
        c1, c2 = st.columns(2)
        cant_i = c1.number_input("Stock Inicial:", min_value=0)
        s_min = c2.number_input("Mínimo para Alerta:", min_value=1)
        
        c3, c4 = st.columns(2)
        costo = c3.number_input("Costo Unitario de Compra ($):", min_value=0.0, format="%.2f")
        venta = c4.number_input("Precio Unitario de Venta ($):", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Guardar Producto"):
            if nombre:
                g_unitaria = venta - costo
                g_total = cant_i * g_unitaria
                nueva_fila = pd.DataFrame({
                    "Nombre": [nombre], "Categoria": [cat], "Cantidad": [cant_i],
                    "Stock_Minimo": [s_min], "Costo_Compra": [costo],
                    "Precio_Venta": [venta], "Ganancia_Unitaria": [g_unitaria],
                    "Ganancia_Total": [g_total]
                })
                df_final = pd.concat([df_inv, nueva_fila], ignore_index=True)
                conn.update(worksheet="Inventario", data=df_final)
                st.success("Producto registrado exitosamente.")

# ---------------- 4. CLIENTES ----------------
elif choice == "Cuentas por Cobrar (Clientes)":
    st.subheader("👤 Clientes con Pagos Pendientes")
    clientes = df_deudas[df_deudas['Tipo'] == "Cliente"]
    if not clientes.empty:
        st.metric("Total por Cobrar", f"${pd.to_numeric(clientes['Monto']).sum():,.2f}")
        cliente_sel = st.selectbox("Selecciona un cliente:", clientes['Nombre'].unique())
        st.table(clientes[clientes['Nombre'] == cliente_sel][['Producto', 'Cantidad', 'Monto']])
    else:
        st.info("No hay deudas de clientes.")

# ---------------- 5. PROVEEDORES ----------------
elif choice == "Cuentas por Pagar (Proveedores)":
    st.subheader("🤝 Deudas con Proveedores")
    proveedores = df_deudas[df_deudas['Tipo'] == "Proveedor"]
    if not proveedores.empty:
        st.error(f"Total Pendiente de Pago: ${pd.to_numeric(proveedores['Monto']).sum():,.2f}")
        prov_sel = st.selectbox("Selecciona un proveedor:", proveedores['Nombre'].unique())
        st.table(proveedores[proveedores['Nombre'] == prov_sel][['Producto', 'Cantidad', 'Monto']])
    else:
        st.success("Estás al día con tus proveedores.")

# ---------------- 6. NUEVA DEUDA E INVENTARIO ----------------
elif choice == "Registrar Nueva Deuda":
    st.subheader("📝 Registrar deuda y actualizar inventario")
    
    if not df_inv.empty:
        tipo = st.selectbox("¿Es un Cliente o un Proveedor?", ["Cliente", "Proveedor"])
        nombre = st.text_input("Nombre de la persona/empresa:")
        producto_seleccionado = st.selectbox("Producto involucrado:", df_inv['Nombre'].tolist())
        
        # Obtener los datos actuales del producto desde el Excel
        idx = df_inv.index[df_inv['Nombre'] == producto_seleccionado].tolist()[0]
        precio_venta = df_inv.at[idx, 'Precio_Venta']
        costo_compra = df_inv.at[idx, 'Costo_Compra']
        stock_actual = df_inv.at[idx, 'Cantidad']
        ganancia_uni = df_inv.at[idx, 'Ganancia_Unitaria']
        
        # Decidir qué precio usar según a quién le registramos la deuda
        precio_usar = precio_venta if tipo == "Cliente" else costo_compra
        
        cant = st.number_input("Cantidad de producto:", min_value=1, step=1)
        
        # El sistema multiplica solo
        monto_calculado = cant * precio_usar
        st.info(f"💰 Monto total de la deuda: **${monto_calculado:,.2f}** (Calculado a ${precio_usar:,.2f} c/u)")
        
        if st.button("Guardar Deuda y Actualizar Stock"):
            if nombre:
                # Validar que tengamos stock si es un cliente llevándose mercancía
                if tipo == "Cliente" and stock_actual < cant:
                    st.error(f"❌ Error: No puedes fiar {cant} unidades. Solo tienes {stock_actual} de {producto_seleccionado} en almacén.")
                else:
                    # 1. Guardar la deuda en la hoja de deudas
                    nueva_deuda = pd.DataFrame({"Tipo": [tipo], "Nombre": [nombre], "Producto": [producto_seleccionado], "Cantidad": [cant], "Monto": [monto_calculado]})
                    df_final_deudas = pd.concat([df_deudas, nueva_deuda], ignore_index=True)
                    conn.update(worksheet="Registro_Deudas", data=df_final_deudas)
                    
                    # 2. Actualizar el stock en la hoja de inventario
                    nuevo_stock = stock_actual - cant if tipo == "Cliente" else stock_actual + cant
                    df_inv.at[idx, 'Cantidad'] = nuevo_stock
                    df_inv.at[idx, 'Ganancia_Total'] = nuevo_stock * ganancia_uni
                    conn.update(worksheet="Inventario", data=df_inv)
                    
                    st.success(f"✅ Listo. Deuda guardada y stock de {producto_seleccionado} actualizado a {nuevo_stock}.")
    else:
        st.warning("Primero debes agregar productos al inventario.")
