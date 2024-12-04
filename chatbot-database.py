import ollama
import streamlit as st
import mysql.connector
import pandas as pd
import matplotlib.pyplot as plt

# Configuración inicial
st.title("Chatbot de la Armada del Ecuador")

# Inicializar historial y modelo
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Inicializar historial y modelo
if "messages_user" not in st.session_state:
    st.session_state["messages_user"] = []

if "model" not in st.session_state:
    st.session_state["model"] = ""

models = [model["model"] for model in ollama.list()["models"]]
st.session_state["model"] = st.selectbox("Elige tu modelo", models)

# Función para conectarse a la base de datos MySQL
def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root",
            database="armada_database"
        )
        return connection
    except mysql.connector.Error as e:
        st.error(f"Error conectando a la base de datos: {e}")
        message = st.write_stream(model_res_generator())
        return None

# Función para ejecutar consultas SQL
def execute_sql_query(query):
    connection = connect_to_database()
    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            connection.close()
            return pd.DataFrame(rows, columns=columns)
        except mysql.connector.Error as e:
            return 0
    return None

# Generador de respuestas del modelo
def model_res_generator():
    stream = ollama.chat(
        model=st.session_state["model"],
        messages=st.session_state["messages"],
        stream=True,
    )
    for chunk in stream:
        yield chunk["message"]["content"]

# Mostrar mensajes del historial en la app
for message in st.session_state["messages_user"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Función para generar gráficos automáticamente
def generate_automatic_plot(dataframe):
    try:
        # Verificar si el dataframe está vacío
        if dataframe.empty:
            st.error("El DataFrame está vacío.")
            return

        # Identificar el número de columnas del dataframe
        num_columns = len(dataframe.columns)

        # Si el DataFrame tiene 2 columnas, hacer un gráfico de barras
        if num_columns == 2:
            x_col = dataframe.columns[0]
            y_col = dataframe.columns[1]

            # Asegurarnos de que la columna x sea categórica para gráfico de barras
            dataframe[x_col] = dataframe[x_col].astype('category')

            fig, ax = plt.subplots(figsize=(10, 6))
            dataframe.groupby(x_col, observed=False)[y_col].mean().sort_index().plot(kind='bar', ax=ax)
            ax.set_title(f'{y_col} por {x_col}')
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col)
            plt.xticks(rotation=45)
            plt.tight_layout()
            st.pyplot(fig)  # Mostrar gráfico en Streamlit

        # Si el DataFrame tiene 3 columnas, hacer un gráfico lineal
        elif num_columns == 3:
            x_col = dataframe.columns[0]
            y_col1 = dataframe.columns[1]
            y_col2 = dataframe.columns[2]

            # Ordenar los datos según la columna x para coherencia
            dataframe_sorted = dataframe.sort_values(by=x_col)

            # Crear gráfico lineal: x_col vs y_col1
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(dataframe_sorted[x_col], dataframe_sorted[y_col1], label=f'{y_col1} vs {x_col}', marker='o')
            ax.set_title(f'{y_col1} vs {x_col}')
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col1)
            ax.legend()
            plt.tight_layout()
            st.pyplot(fig)  # Mostrar gráfico en Streamlit

            # Crear gráfico lineal: x_col vs y_col2
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(dataframe_sorted[x_col], dataframe_sorted[y_col2], label=f'{y_col2} vs {x_col}', marker='o', color='orange')
            ax.set_title(f'{y_col2} vs {x_col}')
            ax.set_xlabel(x_col)
            ax.set_ylabel(y_col2)
            ax.legend()
            plt.tight_layout()
            st.pyplot(fig)  # Mostrar gráfico en Streamlit

        else:
            st.error("El DataFrame debe tener 2 o 3 columnas para generar los gráficos.")

    except Exception as e:
        st.error(f"Ocurrió un error generando la gráfica: {e}")


# Intentos maximos
max_attempts = 1
# Entrada del usuario
if prompt := st.chat_input("¿Qué deseas consultar?"):
    # Entrada de user por default para consulta de base de datos
    prompt_for_database = f"""
    Dada una consulta en lenguaje natural: {prompt}, traduce la siguiente instrucción en un comando SQL para conectarte a la base de datos mySQL llamada `armada_database` y acceder a la tabla `armada`. La tabla contiene las siguientes columnas:
    `tiempo`, `tiemposuministro`, `caudal`, `presion`, `muellenum`.

    Asegúrate de que la consulta sea precisa, por ejemplo, para filtrar registros por muelle, tiempo, caudal o presión, y extraer solo los datos necesarios para la consulta en cuestión. 
    Retorna solo el comando SQL en bruto, sin comentarios ni títulos adicionales.

    Ejemplo de consulta para mostrar las 10 primeras filas:/n
    Respuesta en raw:'SELECT * FROM armada_database.armada LIMIT 10;'\n

    Ejemplos de Consultas SQL Basadas en el Prompt:
    Consulta para obtener el caudal promedio por muelle:

    Prompt natural: "Obtén el caudal promedio de suministro de combustible por muelle."
    Consulta SQL:
    SELECT muellenum, AVG(caudal) AS caudal_promedio FROM armada GROUP BY muellenum;
    Consulta para obtener los registros de suministro por un tiempo específico:

    Prompt natural: "Obtén todos los registros de suministro de combustible realizados el 10 de diciembre de 2024."
    Consulta SQL:
    SELECT * FROM armada WHERE tiempo = '2024-12-10';
    Consulta para obtener los registros de suministro en un muelle específico durante un rango de fechas:

    Prompt natural: "Obtén los registros de suministro de combustible en el muelle número 3 entre el 1 de diciembre y el 5 de diciembre."
    Consulta SQL:
    SELECT * FROM armada WHERE muellenum = 3 AND tiempo BETWEEN '2024-12-01' AND '2024-12-05';"""

    prompt_for_report = f"""
    {prompt}
    Genera un reporte detallado sobre la base de datos `armada_database` y la tabla `armada`. Esta tabla tiene las siguientes columnas:
    `tiempo`, `tiemposuministro`, `caudal`, `presion`, `muellenum`.

    Para generar el reporte, por favor indícame el muelle o el rango de tiempo que deseas analizar, y qué aspectos específicos te gustaría explorar en detalle (por ejemplo, caudal, presión, duración del suministro, etc.).

    Una vez que me proporciones esa información, generaré una consulta SQL para extraer los datos necesarios y elaborar el reporte con los siguientes puntos:

    1. **Resumen del reporte**:
        - Información clave sobre el suministro de combustible (muelle, caudal, duración).
        - Tendencias o anomalías detectadas en el tiempo.

    2. **Análisis de los datos**:
        - Hallazgos interesantes o patrones en los datos de suministro.
        - Comparación entre muelles o entre diferentes períodos de tiempo.
        - Análisis del caudal y la presión en diferentes muelles.

    3. **Recomendaciones**:
        - Sugerencias para mejorar la eficiencia del suministro de combustible.
        - Identificación de muelles que requieren mantenimiento o mejora en el rendimiento.

    Ejemplo de formato de reporte:

    Reporte #1 Fecha de emisión: 2024-12-10

    Resumen del reporte

    - **Muelle**: Muelle número 2
    - **Tiempo de suministro**: 2 horas
    - **Caudal**: 50 litros/minuto
    - **Presión**: 150 bar

    Análisis de los datos

    - El muelle número 2 tuvo un suministro constante de combustible con un caudal de 50 litros por minuto durante un total de 2 horas. La presión en ese muelle se mantuvo en 150 bar, dentro del rango esperado.
    - No se detectaron variaciones significativas en el caudal ni en la presión durante este período.

    Recomendaciones

    - Se recomienda aumentar la capacidad de suministro en los muelles con caudal más bajo para satisfacer la demanda.
    - Realizar una inspección regular de la presión en los muelles para asegurar que se mantenga dentro de los parámetros óptimos.\n

    Ejemplo de Reporte Generado:
    Supongamos que el reporte se solicita para el Muelle número 2 durante un rango de fechas específico, el reporte generado podría ser algo así:

    Reporte #1 Fecha de emisión: 2024-12-10

    Resumen del reporte:

    Muelle: Muelle número 2
    Tiempo de suministro: 2 horas
    Caudal: 50 litros/minuto
    Presión: 150 bar
    Análisis de los datos:

    El muelle número 2 ha tenido un suministro constante de combustible con un caudal de 50 litros por minuto durante 2 horas. La presión en este muelle ha permanecido en 150 bar, dentro del rango óptimo.
    No se han observado anomalías en el comportamiento de caudal ni presión en este periodo.
    Recomendaciones:

    Para optimizar el suministro, se recomienda evaluar la capacidad de otros muelles con caudales más bajos y asegurarse de que no haya cuellos de botella en el sistema.
    Es aconsejable realizar un mantenimiento preventivo en el sistema de presión para evitar futuros problemas en el suministro.
    """
    
    if "consulta" in prompt.lower() or "base de datos" in prompt.lower():
        st.session_state["messages"].append({"role": "user", "content": prompt_for_database})
        st.session_state["messages_user"].append({"role": "user", "content": prompt})
    else:
        st.session_state["messages"].append({"role": "user", "content": prompt})
        st.session_state["messages_user"].append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        message = st.write_stream(model_res_generator())
        st.session_state["messages"].append({"role": "assistant", "content": message})
        st.session_state["messages_user"].append({"role": "assistant", "content": message})              
        if ("SELECT" in message.upper()):
            with st.spinner("Generando consulta SQL..."):
                attempts = 0
                while attempts < max_attempts:
                    try:
                        query_result = execute_sql_query(message)
                        if not query_result.empty:
                            st.session_state["messages"].append({"role": "assistant", "content": message})
                            st.session_state["messages_user"].append({"role": "assistant", "content": message})
                            st.session_state["messages"].append({"role": "assistant", "content": query_result})   
                            st.write("Resultados de la consulta:")
                            st.dataframe(query_result)
                            print(query_result)
                            attempts += 1
                            if "reporte" in prompt.lower():
                                prompt += f"{prompt} usa estos datos para extraer la información que se te pide: {query_result}\n"
                                st.session_state["messages"].append({"role": "user", "content": prompt_for_report})
                                st.session_state["messages_user"].append({"role": "user", "content": prompt})
                                break
                            # Generar gráfica solo si la entrada menciona "grafica"
                            if "grafica" in prompt.lower():
                                generate_automatic_plot(query_result)
                                break

                        elif query_result==0:
                            prompt = """Fallaste, yo solo quiero el comando SQL en raw,
                                        no quiero comentarios ni titulos adicionales, quiero solamente algo como SELECT .*?"""
                            st.session_state["messages"].append({"role": "user", "content": prompt})
                            message = model_res_generator()
                            query_result = execute_sql_query(message)
                            st.write("Intentando generar dataframe...")
                            attempts += 1 
                        elif query_result.empty:
                            st.write("No se obtuvo respuesta alguna")
                    except Exception as e:
                        st.write("No se pudo obtener el dataframe")
                        attempts +=1

            