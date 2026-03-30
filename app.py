import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Gestión Agro", page_icon="🌱", layout="wide")
st.title("🌱 Sistema Integral Agro: Inventario y Deudas")

# 1. Conectar a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df_inv = conn.read(worksheet="Inventario", ttl=0).dropna(how="all")
df_deudas = conn.read(worksheet="Registro_Deudas", ttl=0).dropna(how="all")

# Si la hoja de deudas está totalmente vacía, creamos las columnas para evitar errores
if df_deudas.empty or 'Tipo' not in df_deudas.columns:
    df_deudas = pd.DataFrame(columns=['Tipo', 'Nombre', 'Producto', 'Cantidad', 'Monto'])

# Forzar números en el inventario
cols_num = ['Cantidad', 'Stock_Minimo', 'Costo_Compra', 'Precio_Venta', 'Ganancia_Unitaria', 'Ganancia_Total']
for col in cols_num:
    if col in df_inv.columns:
        df_inv[col] = pd.to_numeric(df_inv[col], errors='coerce').fillna(0)

# 2. Menú Lateral
menu = [
    "1. Resumen de Inventario", 
    "2. Registrar Producto Nuevo", 
    "3. Movimiento al Contado", 
    "4. Registrar Deuda (Crédito)", 
    "5. Clientes (Por Cobrar)", 
    "6. Proveedores (Por Pagar)"
]
choice = st.sidebar.radio("Menú Principal", menu)
st.write("---")

# ---------------- 1. RESUMEN ----------------
if choice == "1. Resumen de Inventario":
    st.subheader("📈 Estado del Almacén")
    if not df_inv.empty:
        inversion = (df_inv['Cantidad'] * df_inv['Costo_Compra']).sum()
        ganancia = df_inv['Ganancia_Total'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Inversión en Almacén", f"${inversion:,.2f}")
        c2.metric("Ganancia Proyectada", f"${ganancia:,.2f}")
        c3.metric("Alertas de Stock", len(df_inv[df_inv['Cantidad'] <= df_inv['Stock_Minimo']]))
        
        st.dataframe(df_inv, use_container_width=True)
    else:
        st.info("Inventario vacío. Ve a 'Registrar Producto Nuevo'.")

# ---------------- 2. PRODUCTO NUEVO ----------------
elif choice == "2. Registrar Producto Nuevo":
    st.subheader("➕ Agregar Producto al Catálogo")
    with st.form("nuevo_p"):
        nombre = st.text_input("Nombre del Producto:")
        cat = st.selectbox("Categoría:", ["Agroquímico", "Fertilizante", "Semilla", "Herramienta"])
        c1, c2 = st.columns(2)
        cant_i = c1.number_input("Stock Inicial:", min_value=0)
        s_min = c2.number_input("Aviso Stock Mínimo:", min_value=1)
        
        c3, c4 = st.columns(2)
        costo = c3.number_input("Costo de Compra ($):", min_value=0.0, format="%.2f")
        venta = c4.number_input("Precio de Venta ($):", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("Guardar Producto"):
            if nombre:
                g_uni = venta - costo
                g_tot = cant_i * g_uni
                nueva_fila = pd.DataFrame({
                    "Nombre": [nombre], "Categoria": [cat], "Cantidad": [cant_i],
                    "Stock_Minimo": [s_min], "Costo_Compra": [costo],
                    "Precio_Venta": [venta], "Ganancia_Unitaria": [g_uni], "Ganancia_Total": [g_tot]
                })
                df_inv = pd.concat([df_inv, nueva_fila], ignore_index=True)
                conn.update(worksheet="Inventario", data=df_inv)
                st.success("✅ Producto guardado.")

# ---------------- 3. CONTADO ----------------
elif choice == "3. Movimiento al Contado":
    st.subheader("🔄 Compra/Venta al instante (Sin deuda)")
    if not df_inv.empty:
        prod = st.selectbox("Producto:", df_inv['Nombre'].tolist())
        tipo = st.radio("Acción:", ("Venta (Resta stock)", "Compra (Suma stock)"))
        cant = st.number_input("Cantidad:", min_value=1, step=1)
        
        if st.button("Actualizar Almacén"):
            idx = df_inv.index[df_inv['Nombre'] == prod].tolist()[0]
            stock_actual = df_inv.at[idx, 'Cantidad']
            
            nuevo_stock = stock_actual - cant if "Venta" in tipo else stock_actual + cant
                
            if nuevo_stock < 0:
                st.error("❌ No tienes stock suficiente para esta venta.")
            else:
                df_inv.at[idx, 'Cantidad'] = nuevo_stock
                df_inv.at[idx, 'Ganancia_Total'] = nuevo_stock * df_inv.at[idx, 'Ganancia_Unitaria']
                conn.update(worksheet="Inventario", data=df_inv)
                st.success(f"✅ Almacén actualizado. Hay {nuevo_stock} unidades de {prod}.")
                st.rerun()

# ---------------- 4. REGISTRAR DEUDA (CRÉDITO) ----------------
elif choice == "4. Registrar Deuda (Crédito)":
    st.subheader("📝 Registrar fiao y descontar mercancía")
    if not df_inv.empty:
        tipo_deuda = st.selectbox("¿A quién le vas a registrar la cuenta?", ["Cliente (Me debe)", "Proveedor (Le debo)"])
        tipo_real = "Cliente" if "Cliente" in tipo_deuda else "Proveedor"
        
        nombre = st.text_input("Nombre de la persona/empresa:")
        producto = st.selectbox("Producto:", df_inv['Nombre'].tolist())
        
        # Buscar precios automáticamente
        idx = df_inv.index[df_inv['Nombre'] == producto].tolist()[0]
        precio_usar = df_inv.at[idx, 'Precio_Venta'] if tipo_real == "Cliente" else df_inv.at[idx, 'Costo_Compra']
        
        cant = st.number_input("Cantidad entregada/recibida:", min_value=1, step=1)
        
        # Calcular el monto matemático en vivo
        monto_calc = cant * precio_usar
        st.info(f"💰 Monto automático a registrar: **${monto_calc:,.2f}** (Calculado a ${precio_usar:,.2f} c/u)")
        
        if st.button("Guardar Deuda y Actualizar Inventario"):
            if nombre:
                stock_actual = df_inv.at[idx, 'Cantidad']
                
                # Si es cliente, verificamos que haya inventario para fiar
                if tipo_real == "Cliente" and stock_actual < cant:
                    st.error(f"❌ No puedes fiar {cant}. Solo tienes {stock_actual} en almacén.")
                else:
                    # 1. Guardar deuda
                    nueva_deuda = pd.DataFrame({"Tipo": [tipo_real], "Nombre": [nombre], "Producto": [producto], "Cantidad": [cant], "Monto": [monto_calc]})
                    df_deudas = pd.concat([df_deudas, nueva_deuda], ignore_index=True)
                    conn.update(worksheet="Registro_Deudas", data=df_deudas)
                    
                    # 2. Descontar o Sumar al inventario
                    nuevo_stock = stock_actual - cant if tipo_real == "Cliente" else stock_actual + cant
                    df_inv.at[idx, 'Cantidad'] = nuevo_stock
                    df_inv.at[idx, 'Ganancia_Total'] = nuevo_stock * df_inv.at[idx, 'Ganancia_Unitaria']
                    conn.update(worksheet="Inventario", data=df_inv)
                    
                    st.success(f"✅ Deuda registrada. Almacén de {producto} actualizado a {nuevo_stock}.")

# ---------------- 5. CLIENTES (BORRAR/LIQUIDAR) ----------------
elif choice == "5. Clientes (Por Cobrar)":
    st.subheader("👤 Cuentas por Cobrar")
    clientes = df_deudas[df_deudas['Tipo'] == "Cliente"]
    
    if not clientes.empty:
        st.metric("Plata en la calle (Total)", f"${pd.to_numeric(clientes['Monto']).sum():,.2f}")
        cliente_sel = st.selectbox("Selecciona un cliente:", clientes['Nombre'].unique())
        
        deudas_cliente = clientes[clientes['Nombre'] == cliente_sel]
        st.table(deudas_cliente[['Producto', 'Cantidad', 'Monto']])
        
        st.write("¿Ya pagó toda su cuenta?")
        if st.button(f"🗑️ Liquidar (Borrar) cuenta de {cliente_sel}"):
            # Filtramos para eliminar a ese cliente de la base de datos
            df_deudas = df_deudas[~((df_deudas['Tipo'] == "Cliente") & (df_deudas['Nombre'] == cliente_sel))]
            conn.update(worksheet="Registro_Deudas", data=df_deudas)
            st.success("✅ Cuenta liquidada y borrada.")
            st.rerun()
    else:
        st.success("Nadie te debe dinero.")

# ---------------- 6. PROVEEDORES (BORRAR/LIQUIDAR) ----------------
elif choice == "6. Proveedores (Por Pagar)":
    st.subheader("🤝 Cuentas por Pagar")
    proveedores = df_deudas[df_deudas['Tipo'] == "Proveedor"]
    
    if not proveedores.empty:
        st.error(f"Total que debes: ${pd.to_numeric(proveedores['Monto']).sum():,.2f}")
        prov_sel = st.selectbox("Selecciona un proveedor:", proveedores['Nombre'].unique())
        
        deudas_prov = proveedores[proveedores['Nombre'] == prov_sel]
        st.table(deudas_prov[['Producto', 'Cantidad', 'Monto']])
        
        st.write("¿Ya le pagaste a este proveedor?")
        if st.button(f"🗑️ Liquidar (Borrar) cuenta de {prov_sel}"):
            df_deudas = df_deudas[~((df_deudas['Tipo'] == "Proveedor") & (df_deudas['Nombre'] == prov_sel))]
            conn.update(worksheet="Registro_Deudas", data=df_deudas)
            st.success("✅ Cuenta pagada y borrada.")
            st.rerun()
    else:
        st.success("No le debes a nadie.")
