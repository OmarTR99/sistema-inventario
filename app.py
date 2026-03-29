import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. Diseño de la página principal
st.set_page_config(page_title="Inventario Agronómico", page_icon="🌱")
st.title("🌱 Sistema de Inventario Agronómico")
st.write("Gestión de entradas, salidas y existencias.")

# 2. Conexión a Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet="Inventario", ttl=0)

# Limpiar filas vacías
df = df.dropna(how="all")

# 3. Menú lateral
st.sidebar.title("Menú de Opciones")
menu = ["Ver Inventario y Alertas", "Registrar Movimiento", "Agregar Producto Nuevo"]
eleccion = st.sidebar.radio("¿Qué deseas hacer?", menu)

st.write("---")

# ---------------- SECCIÓN 1: VER INVENTARIO ----------------
if eleccion == "Ver Inventario y Alertas":
    st.subheader("📦 Estado Actual del Inventario")
    
    if not df.empty:
        df['Cantidad'] = pd.to_numeric(df['Cantidad'])
        df['Stock_Minimo'] = pd.to_numeric(df['Stock_Minimo'])
        
        bajos_stock = df[df['Cantidad'] <= df['Stock_Minimo']]
        
        if not bajos_stock.empty:
            st.error("⚠️ ALERTA: Los siguientes productos han alcanzado su límite mínimo:")
            st.dataframe(bajos_stock[['Nombre', 'Cantidad', 'Stock_Minimo']], use_container_width=True)
        else:
            st.success("✅ Todo el inventario cuenta con existencias suficientes.")
        
        st.write("**Todos los productos disponibles:**")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("El inventario está vacío. Ve a 'Agregar Producto Nuevo' para empezar.")

# ---------------- SECCIÓN 2: REGISTRAR MOVIMIENTO ----------------
elif eleccion == "Registrar Movimiento":
    st.subheader("🔄 Entrada y Salida de Mercancía")
    
    if not df.empty:
        producto_seleccionado = st.selectbox("1. Selecciona el producto:", df['Nombre'].tolist())
        tipo_movimiento = st.radio("2. Tipo de movimiento:", ("Entrada (Suma)", "Salida (Resta)"))
        cantidad_mov = st.number_input("3. Cantidad:", min_value=1, step=1)
        
        if st.button("Registrar Movimiento"):
            idx = df.index[df['Nombre'] == producto_seleccionado].tolist()[0]
            stock_actual = int(df.at[idx, 'Cantidad'])
            
            if "Entrada" in tipo_movimiento:
                nuevo_stock = stock_actual + cantidad_mov
            else:
                nuevo_stock = stock_actual - cantidad_mov
            
            if nuevo_stock < 0:
                st.error("❌ Error: No puedes sacar más mercancía de la que hay.")
            else:
                df.at[idx, 'Cantidad'] = nuevo_stock
                conn.update(worksheet="Inventario", data=df)
                st.success(f"✅ Movimiento registrado. El nuevo stock de **{producto_seleccionado}** es: {nuevo_stock}")
                st.rerun()
    else:
        st.warning("Primero debes agregar productos.")

# ---------------- SECCIÓN 3: AGREGAR PRODUCTO ----------------
elif eleccion == "Agregar Producto Nuevo":
    st.subheader("➕ Añadir Nuevo Producto")
    
    nombre = st.text_input("Nombre del producto (ej. Fertilizante Urea):")
    categoria = st.selectbox("Categoría:", ["Agroquímico", "Semilla", "Fertilizante", "Herramienta", "Otro"])
    
    col1, col2 = st.columns(2)
    with col1:
        cantidad_inicial = st.number_input("Cantidad inicial en almacén:", min_value=0, step=1)
    with col2:
        stock_minimo = st.number_input("¿En qué cantidad debe dispararse la alerta?:", min_value=0, step=1)
    
    if st.button("Guardar Producto Nuevo"):
        if nombre != "":
            nuevo_producto = pd.DataFrame({
                "Nombre": [nombre],
                "Categoria": [categoria],
                "Cantidad": [cantidad_inicial],
                "Stock_Minimo": [stock_minimo]
            })
            df_actualizado = pd.concat([df, nuevo_producto], ignore_index=True)
            conn.update(worksheet="Inventario", data=df_actualizado)
            st.success(f"✅ Producto '{nombre}' agregado exitosamente.")
        else:
            st.error("Por favor, escribe el nombre del producto.")
