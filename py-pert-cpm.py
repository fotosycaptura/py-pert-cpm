#!/usr/bin/env python3
##############################################################
# Programa desarrollado por @fotosycaptura                   #
# Informar bugs o sugerencias                                #
# Requiere Python 3.13.2 para su funcionamiento              #
##############################################################

import pandas as pd
from collections import defaultdict, deque
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# === PARTE 1: Cálculo PERT/CPM ===

# Leer archivo CSV
df = pd.read_csv("datos.csv")

# Limpiar columnas
df['CODE'] = df['CODE'].astype(str).str.strip()
df['PREDECESORES'] = df['PREDECESORES'].fillna('').astype(str).str.strip()
df['DIAS'] = pd.to_numeric(df['DIAS'], errors='coerce').fillna(0).astype(int)

# Procesar correctamente los predecesores
def procesar_predecesores(celda):
    celda = celda.strip()
    if not celda:
        return []
    if ',' in celda:
        return [p.strip() for p in celda.split(',') if p.strip()]
    if ' ' in celda:
        return [p.strip() for p in celda.split(' ') if p.strip()]
    return list(celda.strip())  # Caso como 'DF' → ['D', 'F']

df['predecesores'] = df['PREDECESORES'].apply(procesar_predecesores)

# Crear diccionario de tareas
tareas = df.set_index('CODE').to_dict('index')

# Limpiar predecesores inválidos
for codigo, info in tareas.items():
    info['predecesores'] = [p for p in info['predecesores'] if p in tareas]
    tareas[codigo] = info

# FORWARD PASS (ES y EF)
for codigo in df['CODE']:
    tarea = tareas[codigo]
    if not tarea['predecesores']:
        tarea['ES'] = 0
    else:
        tarea['ES'] = max(tareas[p]['EF'] for p in tarea['predecesores'])
    tarea['EF'] = tarea['ES'] + tarea['DIAS']
    tareas[codigo] = tarea

# Duración total del proyecto
duracion_total = max(t['EF'] for t in tareas.values())

# Construir sucesores y orden topológico inverso
sucesores_dict = defaultdict(list)
entradas = {codigo: 0 for codigo in df['CODE']}

for codigo, info in tareas.items():
    for pred in info['predecesores']:
        sucesores_dict[pred].append(codigo)
        entradas[codigo] += 1

cola = deque([codigo for codigo, v in entradas.items() if v == 0])
orden_topologico = []

while cola:
    actual = cola.popleft()
    orden_topologico.append(actual)
    for sucesor in sucesores_dict[actual]:
        entradas[sucesor] -= 1
        if entradas[sucesor] == 0:
            cola.append(sucesor)

# BACKWARD PASS (LS y LF)
for codigo in reversed(orden_topologico):
    tarea = tareas[codigo]
    sucesores = sucesores_dict[codigo]
    if not sucesores:
        tarea['LF'] = duracion_total
    else:
        tarea['LF'] = min(tareas[s]['LS'] for s in sucesores)
    tarea['LS'] = tarea['LF'] - tarea['DIAS']
    tarea['MARGEN'] = tarea['LS'] - tarea['ES']
    tarea['CRITICO'] = tarea['MARGEN'] == 0
    tareas[codigo] = tarea

# Armar DataFrame final
resultado = []
for codigo in df['CODE']:
    t = tareas[codigo]
    resultado.append({
        'DESC': t['DESC'],
        'CODE': codigo,
        'PRED': ', '.join(t['predecesores']),
        'DIAS': t['DIAS'],
        'ES': t['ES'],
        'EF': t['EF'],
        'LS': t['LS'],
        'LF': t['LF'],
        'MARGEN': t['MARGEN'],
        'CRITICO?': 'SI' if t['CRITICO'] else 'NO'
    })

df_resultado = pd.DataFrame(resultado)
df_resultado.to_csv("resultado_pert_cpm.csv", index=False)
print(df_resultado)
print('')
print('ES: Inicio temprano')
print('EF: Fin temprano')
print('LF: Inicio tardío')
print('LS: Fin tardío')

# === PARTE 2: Visualización del diagrama PERT/CPM ===

# Crear grafo
G = nx.DiGraph()
for codigo in df['CODE']:
    t = tareas[codigo]
    etiqueta = (
        f"{codigo}\n"
        f"DUR: {t['DIAS']}\n"
        f"ES:{t['ES']} EF:{t['EF']}\n"
        f"LS:{t['LS']} LF:{t['LF']}\n"
        f"MARGEN:{t['MARGEN']}"
    )
    G.add_node(codigo, label=etiqueta)

for codigo, info in tareas.items():
    for pred in info['predecesores']:
        G.add_edge(pred, codigo)

# Posicionamiento

pos = nx.kamada_kawai_layout(G)

# Colores: rojo si es crítica
color_map = ['red' if tareas[n]['CRITICO'] else 'lightgray' for n in G.nodes]

# Dibujar
plt.figure(figsize=(14, 10))
nx.draw(G, pos, with_labels=True,
        labels=nx.get_node_attributes(G, 'label'),
        node_color=color_map, node_size=6000,
        font_size=8, font_weight='bold', arrows=True)

# Leyenda de colores
red_patch = mpatches.Patch(color='red', label='Tarea Crítica')
gray_patch = mpatches.Patch(color='lightgray', label='Tarea No Crítica')
plt.legend(handles=[red_patch, gray_patch], loc='upper left')

# Glosario de siglas
leyenda = (
    "ES: Inicio temprano\n"
    "EF: Fin temprano\n"
    "LS: Inicio Tardío\n"
    "LF: Fin Tardío\n"
    "MARGEN: Margen"
)
plt.text(0.01, 0.85, leyenda, transform=plt.gca().transAxes,
         fontsize=10, verticalalignment='baseline',
         bbox=dict(boxstyle="round", facecolor='white', edgecolor='gray'))
plt.title("Diagrama PERT/CPM con detalles por tarea", fontsize=12)

plt.axis('off')

# Guardar imagen
plt.savefig("diagrama_pert_cpm.png", bbox_inches='tight')
plt.show()