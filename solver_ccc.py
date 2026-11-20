"""Calculadora interactiva del ejemplo 8.4 Cosmic Computer Company.

Instalación: python -m pip install scipy numpy
Ejecución:   python calculadora_CCC_interactiva.py

Modelo: programación lineal entera mixta (MILP) con variables de
transporte enteras y decisiones binarias de apertura.
"""

import json
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

DATOS_ORIGINALES = {
    "plantas": ["San Francisco", "Los Ángeles", "Phoenix", "Denver"],
    "tiendas": ["San Diego", "Barstow", "Tucson", "Dallas"],
    "capacidades": [1700, 2000, 1700, 2000],
    "costos_fijos": [70000, 70000, 65000, 70000],
    "demandas": [1700, 1000, 1500, 1200],
    "transportes": [
        [5, 3, 2, 6],
        [4, 7, 8, 10],
        [6, 5, 3, 8],
        [9, 8, 6, 5],
    ],
}


def copia_original():
    return json.loads(json.dumps(DATOS_ORIGINALES, ensure_ascii=False))


def validar(datos):
    """Verifica que el conjunto de datos tenga tamaños y valores admisibles."""
    p, t = datos["plantas"], datos["tiendas"]
    if not p or not t or len(set(p)) != len(p) or len(set(t)) != len(t):
        raise ValueError("Debe existir al menos una planta y una tienda, sin nombres repetidos.")
    if len(datos["capacidades"]) != len(p) or len(datos["costos_fijos"]) != len(p):
        raise ValueError("Cada planta debe tener capacidad y costo fijo.")
    if len(datos["demandas"]) != len(t) or len(datos["transportes"]) != len(p):
        raise ValueError("Los tamaños de demanda o de la matriz de transporte no coinciden.")
    if any(len(fila) != len(t) for fila in datos["transportes"]):
        raise ValueError("Cada fila de transporte debe contener un costo por tienda.")
    for clave in ("capacidades", "demandas"):
        for v in datos[clave]:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not float(v).is_integer() or v < 0:
                raise ValueError(f"{clave}: solo se permiten enteros no negativos.")
    for clave in ("costos_fijos",):
        for v in datos[clave]:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v < 0:
                raise ValueError(f"{clave}: solo se permiten números no negativos y finitos.")
    for fila in datos["transportes"]:
        for v in fila:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not np.isfinite(v) or v < 0:
                raise ValueError("Los costos de transporte deben ser números no negativos y finitos.")


def resolver(datos):
    """Resuelve el MILP globalmente; devuelve los cálculos o un error explicativo."""
    validar(datos)
    plantas, tiendas = datos["plantas"], datos["tiendas"]
    n, m = len(plantas), len(tiendas)
    capacidad = np.array(datos["capacidades"], dtype=float)
    demanda = np.array(datos["demandas"], dtype=float)
    fijos = np.array(datos["costos_fijos"], dtype=float)
    costos = np.array(datos["transportes"], dtype=float)

    if sum(capacidad) < sum(demanda):
        return {"error": ("NO HAY SOLUCIÓN: se necesitan "
                          f"{int(sum(demanda)):,} unidades, pero la capacidad disponible "
                          f"es {int(sum(capacidad)):,}.")}
    if sum(demanda) == 0:
        return {"abiertas": np.zeros(n, dtype=int), "envios": np.zeros((n, m), dtype=int),
                "fijos": 0.0, "transporte": 0.0, "total": 0.0, "estado": "Óptimo"}

    # Vector de decisión: primero todos los x[i,j]; después los y[i].
    nvar = n * m + n
    objetivo = np.concatenate([costos.flatten(), fijos])
    A, limites_inf, limites_sup = [], [], []

    # Suma_j x[i,j] - capacidad[i] * y[i] <= 0.
    for i in range(n):
        fila = np.zeros(nvar)
        fila[i * m:(i + 1) * m] = 1
        fila[n * m + i] = -capacidad[i]
        A.append(fila)
        limites_inf.append(-np.inf)
        limites_sup.append(0.0)

    # Suma_i x[i,j] == demanda[j].
    for j in range(m):
        fila = np.zeros(nvar)
        fila[j:n * m:m] = 1
        A.append(fila)
        limites_inf.append(demanda[j])
        limites_sup.append(demanda[j])

    cotas_inf = np.zeros(nvar)
    cotas_sup = np.concatenate([np.full(n * m, np.inf), np.ones(n)])
    respuesta = milp(
        c=objetivo,
        integrality=np.ones(nvar, dtype=int),  # x enteros e y binarias por cotas [0,1]
        bounds=Bounds(cotas_inf, cotas_sup),
        constraints=LinearConstraint(np.array(A), limites_inf, limites_sup),
        options={"time_limit": 60, "mip_rel_gap": 1e-9},
    )

    if respuesta.status != 0 or respuesta.x is None:
        return {"error": f"No se obtuvo una solución óptima: {respuesta.message}"}

    enteros = np.rint(respuesta.x).astype(int)
    envios = enteros[:n * m].reshape(n, m)
    abiertas = enteros[n * m:]
    # Verificación por si existieran discrepancias numéricas del optimizador.
    if (np.any(envios < 0) or np.any(envios.sum(axis=1) > capacidad * abiertas + 1e-7)
            or np.any(envios.sum(axis=0) != demanda) or np.any((abiertas != 0) & (abiertas != 1))):
        return {"error": "El optimizador devolvió una solución que no pasó la validación."}

    total_fijo = float(np.dot(fijos, abiertas))
    total_transporte = float(np.sum(costos * envios))
    return {"abiertas": abiertas, "envios": envios, "fijos": total_fijo,
            "transporte": total_transporte, "total": total_fijo + total_transporte,
            "estado": "Óptimo"}


def moneda(valor):
    return "${:,.2f}".format(valor).replace(",", "_").replace(".", ",").replace("_", ".")


def mostrar_datos(datos):
    print("\n=== DATOS ACTUALES DEL EJERCICIO CCC ===")
    for i, nombre in enumerate(datos["plantas"]):
        print(f"{i + 1}. {nombre}: capacidad={datos['capacidades'][i]}, "
              f"costo fijo={moneda(datos['costos_fijos'][i])}")
    print("\nDemandas:")
    for j, nombre in enumerate(datos["tiendas"]):
        print(f"{j + 1}. {nombre}: {datos['demandas'][j]} unidades")
    print("\nCostos unitarios de transporte (filas: plantas; columnas: tiendas)")
    print(" " * 17 + " ".join(f"{j + 1:>9}" for j in range(len(datos["tiendas"]))))
    for i, fila in enumerate(datos["transportes"]):
        print(f"{datos['plantas'][i][:16]:16} " + " ".join(f"{c:>9g}" for c in fila))
    print(f"\nCapacidad total: {sum(datos['capacidades']):,} | "
          f"Demanda total: {sum(datos['demandas']):,}")


def mostrar_resultado(datos, resultado):
    print("\n" + "=" * 66)
    print("        SOLUCIÓN DEL PROBLEMA COSMIC COMPUTER COMPANY")
    print("=" * 66)
    if "error" in resultado:
        print(resultado["error"])
        print("Revisa las demandas, las capacidades o los costos ingresados.")
        return

    print("\nPLANTAS ABIERTAS / CERRADAS:")
    for i, nombre in enumerate(datos["plantas"]):
        etiqueta = "ABIERTA" if resultado["abiertas"][i] else "CERRADA"
        print(f"- {nombre}: {etiqueta}")

    print("\nDISTRIBUCIÓN ÓPTIMA (solo rutas con envío):")
    for i, planta in enumerate(datos["plantas"]):
        for j, tienda in enumerate(datos["tiendas"]):
            cantidad = int(resultado["envios"][i, j])
            if cantidad:
                costo = cantidad * datos["transportes"][i][j]
                print(f"- {planta} -> {tienda}: {cantidad:,} computadoras "
                      f"x {moneda(datos['transportes'][i][j])} = {moneda(costo)}")
    print("\nCOMPROBACIÓN DE CAPACIDAD:")
    for i, nombre in enumerate(datos["plantas"]):
        usados = int(sum(resultado["envios"][i, :]))
        print(f"- {nombre}: {usados:,} / "
              f"{datos['capacidades'][i] * resultado['abiertas'][i]:,}")
    print("\nCOMPROBACIÓN DE DEMANDA:")
    for j, nombre in enumerate(datos["tiendas"]):
        recibidos = int(sum(resultado["envios"][:, j]))
        print(f"- {nombre}: {recibidos:,} / {datos['demandas'][j]:,}")
    print("\nRESUMEN ECONÓMICO:")
    print(f"  Costos fijos:         {moneda(resultado['fijos'])}")
    print(f"  Costos de transporte: {moneda(resultado['transporte'])}")
    print(f"  COSTO TOTAL MÍNIMO:   {moneda(resultado['total'])}")
    print("  Estado: solución óptima verificada.")
    print("Nota: pueden existir varias distribuciones con el mismo costo mínimo.")
    print("=" * 66)


def numero(mensaje, entero=False):
    while True:
        cadena = input(mensaje).strip().replace(" ", "")
        try:
            valor = int(cadena) if entero else float(cadena.replace(",", "."))
            if not np.isfinite(valor) or valor < 0:
                raise ValueError
            return valor
        except ValueError:
            print("Dato no válido: ingresa un número no negativo" +
                  (" entero." if entero else ". Usa punto para decimales."))


def elegir(opciones, titulo):
    print("\n" + titulo)
    for pos, item in enumerate(opciones, 1):
        print(f"{pos}. {item}")
    while True:
        opcion = input("Selecciona el número: ").strip()
        if opcion.isdigit() and 1 <= int(opcion) <= len(opciones):
            return int(opcion) - 1
        print("Opción no válida.")


def editar(datos):
    campos = ["Capacidad de una planta", "Costo fijo de una planta",
              "Demanda de una tienda", "Costo de transporte de una ruta"]
    seleccion = elegir(campos, "¿QUÉ DATO CAMBIARÁ EL PROFESOR?")
    if seleccion == 0:
        i = elegir(datos["plantas"], "Planta:")
        datos["capacidades"][i] = numero("Nueva capacidad mensual: ", entero=True)
    elif seleccion == 1:
        i = elegir(datos["plantas"], "Planta:")
        datos["costos_fijos"][i] = numero("Nuevo costo fijo: ")
    elif seleccion == 2:
        j = elegir(datos["tiendas"], "Tienda:")
        datos["demandas"][j] = numero("Nueva demanda: ", entero=True)
    else:
        i = elegir(datos["plantas"], "Planta de origen:")
        j = elegir(datos["tiendas"], "Tienda de destino:")
        datos["transportes"][i][j] = numero("Nuevo costo unitario de transporte: ")
    print("Dato modificado. Ejecuta la opción 2 para calcular la nueva solución.")


def guardar(datos):
    ruta = Path("datos_CCC.json")
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Datos guardados en {ruta.resolve()}")


def cargar():
    ruta = Path("datos_CCC.json")
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        validar(datos)
        print("Datos cargados correctamente.")
        return datos
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"No se pudo cargar el archivo: {exc}")
        return None


def main():
    datos = copia_original()
    print("\nCALCULADORA CCC - UBICACIÓN ÓPTIMA DE PLANTAS")
    print("Ejemplo 8.4 de Mathur y Solow; admite valores modificados.")
    while True:
        print("\nMENÚ PRINCIPAL")
        print("1. Mostrar datos actuales")
        print("2. RESOLVER el ejercicio (con los datos actuales)")
        print("3. CAMBIAR un dato y recalcular")
        print("4. Restablecer todos los datos originales")
        print("5. Guardar los datos modificados (JSON)")
        print("6. Cargar datos guardados (JSON)")
        print("0. Salir")
        opcion = input("Elige una opción: ").strip()
        try:
            if opcion == "1":
                mostrar_datos(datos)
            elif opcion == "2":
                mostrar_resultado(datos, resolver(datos))
            elif opcion == "3":
                editar(datos)
                mostrar_resultado(datos, resolver(datos))
            elif opcion == "4":
                datos = copia_original()
                print("Valores del libro restaurados.")
            elif opcion == "5":
                guardar(datos)
            elif opcion == "6":
                nuevos = cargar()
                if nuevos is not None:
                    datos = nuevos
            elif opcion == "0":
                print("Fin del programa.")
                break
            else:
                print("Selecciona una opción del menú.")
        except (ValueError, KeyError, TypeError) as exc:
            print(f"Error: {exc}")
        except (EOFError, KeyboardInterrupt):
            print("\nOperación cancelada.")
            break


if __name__ == "__main__":
    main()
