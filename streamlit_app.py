import streamlit as st
import pandas as pd
import random
import time
import math

# =====================================================
# CONFIGURACIÓN
# =====================================================

st.set_page_config(
page_title="Simulador Económico Multijugador",
page_icon="🏢",
layout="wide"
)

CLAVE_ADMIN = "profe123"


# =====================================================
# DISEÑO
# =====================================================

st.markdown("""
<style>
.main {
background-color: #f5f7fb;
}
div[data-testid="stMetric"] {
background: white;
padding: 16px;
border-radius: 12px;
border: 1px solid #e5e7eb;
}
.stButton button {
border-radius: 10px;
font-weight: bold;
}
</style>
""", unsafe_allow_html=True)


# =====================================================
# ESTADO COMPARTIDO
# =====================================================

def estado_inicial():
    return {
"fase": "espera",
"max_grupos": 10,
"presupuesto_inicial": 5000.0,
"ronda": 1,
"inicio_ronda": 0,
"precio_proveedor": 10.0,
"indice_mercado": 1.0,
"eventos_ronda": [
"🟢 El mercado abre estable al 100%.",
"🏭 El proveedor fija un precio inicial de 10 €/ud."
],
"ultimo_evento_global": None,
"grupos": {},
"envios_ronda": {},
"ultimo_cierre": None
}


@st.cache_resource
def obtener_estado_sala():
    return estado_inicial()


sala = obtener_estado_sala()


# =====================================================
# FUNCIONES DE DATOS
# =====================================================

def beneficio_acumulado(datos):
    return round(
datos["caja"] - sala["presupuesto_inicial"], 2
)


def ganancias_acumuladas(datos):
    return round(sum(
max(0, h["Beneficio (€)"])
for h in datos["historial"]
), 2)


def perdidas_acumuladas(datos):
    return round(sum(
abs(min(0, h["Beneficio (€)"]))
for h in datos["historial"]
), 2)


def posicion_empresa(nombre):
    ranking = sorted(
sala["grupos"].items(),
key=lambda x: (
beneficio_acumulado(x[1]),
x[1]["caja"]
),
reverse=True
)

for i, (empresa, _) in enumerate(ranking):
    if empresa == nombre:
return i + 1

return None


def tabla_clasificacion():
filas = []

for nombre, datos in sala["grupos"].items():

ultima = (
datos["historial"][-1]
if datos["historial"]
else {}
)

filas.append({
"Empresa": nombre,
"Resultado última ronda (€)": ultima.get(
"Beneficio (€)", 0
),
"Beneficio acumulado (€)": beneficio_acumulado(datos),
"Stock en almacén (uds.)": datos["stock"],
"Unidades vendidas": ultima.get("Vendidas", 0)
})

filas.sort(
key=lambda x: x["Beneficio acumulado (€)"],
reverse=True
)

df = pd.DataFrame(filas)

if not df.empty:
df.insert(
0,
"Posición",
[f"{i+1}º" for i in range(len(df))]
)

return df


# =====================================================
# CERRAR RONDA
# =====================================================

def cerrar_ronda():

evento_global = random.choices(
["ninguno", "apagon", "black_friday", "huelga"],
weights=[75, 8, 10, 7],
k=1
)[0]

mensajes = {
"apagon": "⚡ APAGÓN GENERAL: nadie puede vender.",
"black_friday": "🛍️ BLACK FRIDAY: demanda +50%.",
"huelga": "🚧 HUELGA DE TRANSPORTE: demanda -50%."
}

sala["ultimo_evento_global"] = mensajes.get(
evento_global
)

resultados = []

for nombre, datos in sala["grupos"].items():

decision = sala["envios_ronda"].get(
nombre,
{
"comprar": 0,
"precio": 20.0,
"inversion": 0.0
}
)

comprar = decision["comprar"]
precio = decision["precio"]
inversion = decision["inversion"]

inversion = min(inversion, datos["caja"])

dinero_restante = datos["caja"] - inversion

comprar = min(
comprar,
int(dinero_restante // sala["precio_proveedor"])
)

coste_compra = comprar * sala["precio_proveedor"]

gasto_total = coste_compra + inversion

stock_disponible = datos["stock"] + comprar

# EVENTO INDIVIDUAL

evento = random.choices(
["ninguno", "tornado", "inundacion", "viral", "subvencion"],
weights=[78, 4, 6, 6, 6],
k=1
)[0]

aviso = ""
multiplicador = 1.0
subvencion = 0.0

if evento == "tornado":
aviso = "🌪️ Un tornado ha destruido tu stock."
stock_disponible = 0

elif evento == "inundacion":
perdido = stock_disponible // 2
stock_disponible -= perdido
aviso = f"🌊 Inundación: has perdido {perdido} unidades."

elif evento == "viral":
multiplicador = 1.8
aviso = "📱 ¡Tu empresa se ha hecho viral! Demanda +80%."

elif evento == "subvencion":
subvencion = 400.0
aviso = "🏅 Has recibido una subvención de 400 €."

datos["ultimo_suceso_indiv"] = aviso

# DEMANDA

clientes_base = 80 * sala["indice_mercado"]

bonus_inversion = math.sqrt(inversion) * 2.2

clientes = int(
(clientes_base + bonus_inversion)
* random.uniform(0.92, 1.08)
)

probabilidad = max(
0.05,
min(1.0, (45 - precio) / 30)
)

demanda = int(
clientes * probabilidad * multiplicador
)

if evento_global == "apagon":
demanda = 0

elif evento_global == "black_friday":
demanda = int(demanda * 1.5)

elif evento_global == "huelga":
demanda = int(demanda * 0.5)

vendidas = min(stock_disponible, demanda)

stock_final = stock_disponible - vendidas

ingresos_ventas = vendidas * precio
ingresos_totales = ingresos_ventas + subvencion

beneficio = ingresos_totales - gasto_total

datos["caja"] = round(
datos["caja"] + beneficio,
2
)

datos["stock"] = stock_final

registro = {
"Ronda": sala["ronda"],
"Prov. (€)": sala["precio_proveedor"],
"PVP (€)": precio,
"Compradas": comprar,
"Vendidas": vendidas,
"Demanda": demanda,
"Stock": stock_final,
"Gastos (€)": round(gasto_total, 2),
"Ingresos (€)": round(ingresos_totales, 2),
"Beneficio (€)": round(beneficio, 2),
"Caja (€)": datos["caja"],
"Evento": aviso
}

datos["historial"].append(registro)

resultados.append({
"Empresa": nombre,
"Beneficio": beneficio,
"Stock": stock_final,
"Vendidas": vendidas
})

# ACTUALIZAR MERCADO

var_mercado = random.choice(
[-15, -10, -5, 0, 5, 10, 15, 20]
)

var_proveedor = random.choice(
[-15, -10, -5, 0, 5, 10, 15, 20]
)

sala["indice_mercado"] = round(
max(
0.4,
min(
2.2,
sala["indice_mercado"] *
(1 + var_mercado / 100)
)
),
2
)

sala["precio_proveedor"] = round(
max(
3.0,
sala["precio_proveedor"] *
(1 + var_proveedor / 100)
),
2
)

eventos = []

if var_mercado > 0:
eventos.append(
f"📈 El mercado sube un +{var_mercado}%."
)
elif var_mercado < 0:
eventos.append(
f"📉 El mercado baja un {var_mercado}%."
)
else:
eventos.append("⚖️ El mercado se mantiene estable.")

if var_proveedor > 0:
eventos.append(
f"🚚 El proveedor sube un +{var_proveedor}%. "
f"Nuevo precio: {sala['precio_proveedor']:.2f} €/ud."
)
elif var_proveedor < 0:
eventos.append(
f"🏷️ El proveedor baja un {var_proveedor}%. "
f"Nuevo precio: {sala['precio_proveedor']:.2f} €/ud."
)
else:
eventos.append(
f"🏭 El proveedor mantiene su precio: "
f"{sala['precio_proveedor']:.2f} €/ud."
)

sala["eventos_ronda"] = eventos

sala["ultimo_cierre"] = {
"ronda": sala["ronda"],
"resultados": resultados,
"evento": sala["ultimo_evento_global"]
}

sala["ronda"] += 1
sala["envios_ronda"] = {}
sala["inicio_ronda"] = time.time()


# =====================================================
# CABECERA
# =====================================================

st.title("🏢 Simulador Económico Multijugador")

st.caption(
"Gestiona tu empresa, toma decisiones y compite "
"en el mercado."
)

st.markdown("---")

tab_alumno, tab_admin = st.tabs([
"🎓 Zona de empresas",
"🎛️ Panel del profesor"
])


# =====================================================
# ZONA DE EMPRESAS
# =====================================================

with tab_alumno:

if "empresa_activa" not in st.session_state:
st.session_state.empresa_activa = None

if "autenticado" not in st.session_state:
st.session_state.autenticado = False

# -----------------------------------------------
# ACCESO
# -----------------------------------------------

empresa = st.session_state.empresa_activa

if (
not st.session_state.autenticado
or empresa not in sala["grupos"]
):

st.subheader("🔐 Acceso a tu empresa")

opcion = st.radio(
"¿Qué quieres hacer?",
["Crear empresa", "Entrar en una empresa"],
horizontal=True
)

nombre = st.text_input("Nombre de la empresa")

pin = st.text_input(
"PIN de acceso",
type="password"
)

if st.button(
"Continuar",
type="primary",
use_container_width=True
):

nombre = nombre.strip()

if not nombre or not pin:
st.error("Introduce un nombre y un PIN.")

elif opcion == "Crear empresa":

if sala["fase"] != "espera":
st.error(
"La partida ya ha comenzado."
)

elif len(sala["grupos"]) >= sala["max_grupos"]:
st.error("Se ha alcanzado el límite de empresas.")

elif nombre in sala["grupos"]:
st.error("Ese nombre ya está ocupado.")

else:
sala["grupos"][nombre] = {
"pin": pin,
"caja": float(sala["presupuesto_inicial"]),
"stock": 0,
"historial": [],
"ultimo_suceso_indiv": ""
}

st.session_state.empresa_activa = nombre
st.session_state.autenticado = True

st.success("¡Empresa creada correctamente!")
st.rerun()

else:

if nombre not in sala["grupos"]:
st.error("No existe esa empresa.")

elif sala["grupos"][nombre]["pin"] != pin:
st.error("PIN incorrecto.")

else:
st.session_state.empresa_activa = nombre
st.session_state.autenticado = True
st.rerun()

# -----------------------------------------------
# PANEL PRIVADO
# -----------------------------------------------

else:

datos = sala["grupos"][empresa]

cabecera1, cabecera2 = st.columns([3, 1])

with cabecera1:
st.subheader(f"🏢 {empresa}")
st.caption("Panel financiero privado")

with cabecera2:
if st.button("Cerrar sesión"):
st.session_state.empresa_activa = None
st.session_state.autenticado = False
st.rerun()

if sala["fase"] == "espera":
st.info(
"⏳ Esperando a que el profesor inicie la partida."
)

elif sala["fase"] == "jugando":

st.markdown("---")

st.subheader(f"📊 Ronda {sala['ronda']}")

# MÉTRICAS PRIVADAS

beneficio = beneficio_acumulado(datos)
ultima = (
datos["historial"][-1]
if datos["historial"]
else {}
)

m1, m2, m3, m4 = st.columns(4)

m1.metric(
"💰 Caja disponible",
f"{datos['caja']:,.2f} €"
)

m2.metric(
"📦 Stock en almacén",
f"{datos['stock']} uds."
)

m3.metric(
"📈 Beneficio acumulado",
f"{beneficio:+,.2f} €"
)

m4.metric(
"🏆 Posición",
f"{posicion_empresa(empresa)}º"
)

m5, m6, m7 = st.columns(3)

m5.metric(
"🟢 Ganancias acumuladas",
f"{ganancias_acumuladas(datos):,.2f} €"
)

m6.metric(
"🔴 Pérdidas acumuladas",
f"{perdidas_acumuladas(datos):,.2f} €"
)

m7.metric(
"💵 Último resultado",
f"{ultima.get('Beneficio (€)', 0):+,.2f} €"
)

st.markdown("---")

# INFORMACIÓN DEL MERCADO

st.subheader("🌍 Situación del mercado")

a, b = st.columns(2)

a.metric(
"Precio del proveedor",
f"{sala['precio_proveedor']:.2f} €/ud."
)

b.metric(
"Índice del mercado",
f"{sala['indice_mercado'] * 100:.0f}%"
)

for evento in sala["eventos_ronda"]:
st.info(evento)

if sala["ultimo_evento_global"]:
st.warning(sala["ultimo_evento_global"])

if datos["ultimo_suceso_indiv"]:
st.warning(datos["ultimo_suceso_indiv"])

st.markdown("---")

# DECISIONES EMPRESARIALES

st.subheader("🛒 Decisiones de esta ronda")

with st.form("decisiones_empresa"):

comprar = st.number_input(
"Unidades que quieres comprar",
min_value=0,
max_value=100000,
value=0,
step=10
)

precio = st.number_input(
"Precio de venta por unidad (€)",
min_value=1.0,
max_value=1000.0,
value=20.0,
step=0.5
)

inversion = st.number_input(
"Inversión en publicidad (€)",
min_value=0.0,
max_value=float(datos["caja"]),
value=0.0,
step=100.0
)

enviar = st.form_submit_button(
"📨 Enviar decisiones",
type="primary",
use_container_width=True
)

if enviar:

coste = (
comprar * sala["precio_proveedor"]
)

if coste + inversion > datos["caja"]:
st.error(
"No tienes suficiente dinero para "
"realizar esa operación."
)

else:
sala["envios_ronda"][empresa] = {
"comprar": comprar,
"precio": precio,
"inversion": inversion
}

st.success(
"¡Decisiones enviadas correctamente!"
)

if empresa in sala["envios_ronda"]:
st.success(
"✅ Tus decisiones están registradas. "
"Puedes modificarlas antes del cierre."
)

st.caption(
f"Empresas que han enviado sus decisiones: "
f"{len(sala['envios_ronda'])}/"
f"{len(sala['grupos'])}"
)

# -------------------------------------------
# PARTIDA FINALIZADA
# -------------------------------------------

elif sala["fase"] == "terminada":

st.success("🏁 ¡La simulación ha terminado!")

st.metric(
"Beneficio final",
f"{beneficio_acumulado(datos):+,.2f} €"
)

# -------------------------------------------
# HISTORIAL PRIVADO
# -------------------------------------------

st.markdown("---")
st.subheader("📚 Mi historial empresarial")

if datos["historial"]:

df_historial = pd.DataFrame(
datos["historial"]
)

st.dataframe(
df_historial,
use_container_width=True,
hide_index=True
)

grafico = df_historial[
["Ronda", "Caja (€)", "Beneficio (€)"]
].set_index("Ronda")

st.subheader("📈 Evolución de mi empresa")

st.line_chart(grafico)

else:
st.info(
"Todavía no tienes resultados. "
"Cuando termine la primera ronda aparecerán aquí."
)

# -------------------------------------------
# CLASIFICACIÓN PÚBLICA
# -------------------------------------------

st.markdown("---")
st.subheader("🏆 Clasificación general")

st.caption(
"Todos pueden consultar estos resultados. "
"No se muestran las cajas ni los gastos de otras empresas."
)

df_ranking = tabla_clasificacion()

if not df_ranking.empty:
st.dataframe(
df_ranking,
use_container_width=True,
hide_index=True
)


# =====================================================
# PANEL DEL PROFESOR
# =====================================================

with tab_admin:

if "admin_autenticado" not in st.session_state:
st.session_state.admin_autenticado = False

if not st.session_state.admin_autenticado:

st.subheader("🔐 Acceso del profesor")

clave = st.text_input(
"Contraseña del profesor",
type="password"
)

if st.button("Acceder al panel", type="primary"):

if clave == CLAVE_ADMIN:
st.session_state.admin_autenticado = True
st.rerun()
else:
st.error("Contraseña incorrecta.")

else:

st.subheader("🎛️ Panel de administración")

if st.button("Cerrar sesión del profesor"):
st.session_state.admin_autenticado = False
st.rerun()

# CONFIGURACIÓN

st.markdown("---")
st.subheader("⚙️ Configuración de la partida")

if sala["fase"] == "espera":

c1, c2 = st.columns(2)

with c1:
nuevo_max = st.number_input(
"Máximo de empresas",
min_value=2,
max_value=30,
value=sala["max_grupos"]
)

with c2:
nuevo_presupuesto = st.number_input(
"Presupuesto inicial (€)",
min_value=500.0,
max_value=100000.0,
value=float(sala["presupuesto_inicial"]),
step=500.0
)

if st.button("Guardar configuración"):
sala["max_grupos"] = nuevo_max
sala["presupuesto_inicial"] = nuevo_presupuesto
st.success("Configuración guardada.")
st.rerun()

# CONTROL DE PARTIDA

st.markdown("---")
st.subheader("🎮 Control de la simulación")

st.write(f"**Estado:** {sala['fase']}")
st.write(f"**Empresas inscritas:** {len(sala['grupos'])}")
st.write(f"**Ronda actual:** {sala['ronda']}")

if sala["fase"] == "espera":

if st.button(
"🚀 INICIAR PARTIDA",
type="primary",
use_container_width=True
):

if len(sala["grupos"]) < 1:
st.error("Necesitas al menos una empresa.")
else:
sala["fase"] = "jugando"
sala["inicio_ronda"] = time.time()
st.success("¡Partida iniciada!")
st.rerun()

elif sala["fase"] == "jugando":

st.info(
f"Decisiones recibidas: "
f"{len(sala['envios_ronda'])}/"
f"{len(sala['grupos'])}"
)

if st.button(
"⏹️ CERRAR RONDA Y CALCULAR RESULTADOS",
type="primary",
use_container_width=True
):

cerrar_ronda()
st.success("¡Ronda calculada correctamente!")
st.rerun()

if st.button("🏁 FINALIZAR PARTIDA"):
sala["fase"] = "terminada"
st.rerun()

# CLASIFICACIÓN

st.markdown("---")
st.subheader("🏆 Clasificación de empresas")

df = tabla_clasificacion()

if not df.empty:
st.dataframe(
df,
use_container_width=True,
hide_index=True
)

# INFORMACIÓN PRIVADA DEL PROFESOR

st.markdown("---")
st.subheader("🔎 Datos completos de las empresas")

for nombre, datos in sala["grupos"].items():

with st.expander(f"🏢 {nombre}"):

c1, c2, c3 = st.columns(3)

c1.metric(
"Caja",
f"{datos['caja']:,.2f} €"
)

c2.metric(
"Stock",
f"{datos['stock']} uds."
)

c3.metric(
"Beneficio acumulado",
f"{beneficio_acumulado(datos):+,.2f} €"
)

st.write(
f"Ganancias acumuladas: "
f"{ganancias_acumuladas(datos):,.2f} €"
)

st.write(
f"Pérdidas acumuladas: "
f"{perdidas_acumuladas(datos):,.2f} €"
)

if datos["historial"]:
st.dataframe(
pd.DataFrame(datos["historial"]),
use_container_width=True,
hide_index=True
)

# REINICIAR

st.markdown("---")
st.subheader("🔄 Reiniciar simulación")

st.warning(
"Esta acción elimina las empresas, decisiones "
"e historiales de la partida actual."
)

confirmar = st.checkbox(
"Confirmo que quiero borrar toda la partida."
)

if st.button(
"🗑️ REINICIAR TODO",
disabled=not confirmar
):

sala.clear()
sala.update(estado_inicial())

st.session_state.empresa_activa = None
st.session_state.autenticado = False

st.success("Simulación reiniciada.")
st.rerun()


# =====================================================
# PIE DE PÁGINA
# =====================================================

st.markdown("---")

st.caption(
"🏢 Simulador Económico Multijugador · "
"Herramienta educativa de gestión empresarial"
)
