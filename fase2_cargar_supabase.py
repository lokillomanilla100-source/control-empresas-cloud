#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: fase2_cargar_supabase.py
Descripción: Script de carga relacional de datos a Supabase / PostgreSQL en lotes (batches de 100).
"""

import os
import re
import json
import datetime
from dotenv import load_dotenv
from supabase import create_client

# -----------------------------------------------------------------------------
# Configuración y Constantes
# -----------------------------------------------------------------------------
DATA_DIR = 'data_processed'
BATCH_SIZE = 100

def normalize_name(name):
    """Normaliza razones sociales para comparaciones inflexibles (mayúsculas, sin espacios dobles)."""
    if not name:
        return None
    return re.sub(r'\s+', ' ', str(name).strip().upper())

def get_supabase_client():
    """Inicializa y retorna la instancia del cliente Supabase."""
    load_dotenv()
    url = os.getenv('SUPABASE_URL')
    service_key = os.getenv('SUPABASE_SERVICE_KEY')
    anon_key = os.getenv('SUPABASE_KEY')

    if not url:
        raise ValueError("Error: SUPABASE_URL no está configurado en .env")

    # Usar clave disponible (priorizar JWT 'eyJ...')
    key = None
    if service_key and service_key.startswith('eyJ'):
        key = service_key
    elif anon_key and anon_key.startswith('eyJ'):
        key = anon_key
    elif service_key:
        key = service_key
    elif anon_key:
        key = anon_key

    if not key:
        raise ValueError("Error: No se encontró una clave de Supabase en .env")

    return create_client(url, key)

def load_json_file(filename):
    """Carga un archivo JSON desde /data_processed/."""
    filepath = os.path.join(DATA_DIR, filename)
    if not os.path.exists(filepath):
        print(f"  [!] Advertencia: No se encontró {filepath}")
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def batch_insert(client, table_name, records, batch_size=BATCH_SIZE):
    """Inserta registros en lotes de tamaño batch_size y retorna la respuesta con data de Supabase."""
    total = len(records)
    if total == 0:
        print(f"  [i] Tabla [{table_name}]: 0 registros para insertar.")
        return []

    print(f"\n[+] Insertando {total} registros en la tabla [{table_name}] (lotes de {batch_size})...", flush=True)
    inserted_records = []
    failed_count = 0

    for i in range(0, total, batch_size):
        batch = records[i:i + batch_size]
        try:
            res = client.table(table_name).insert(batch).execute()
            if res.data:
                inserted_records.extend(res.data)
                print(f"  ├─ Lote {i // batch_size + 1}: {len(res.data)} registros insertados ({min(i + batch_size, total)}/{total})")
            else:
                print(f"  ├─ Lote {i // batch_size + 1}: {len(batch)} procesados.")
        except Exception as e:
            failed_count += len(batch)
            err_msg = str(e)
            print(f"  [!] Error en lote {i // batch_size + 1} de [{table_name}]: {err_msg}")
            if "42501" in err_msg or "row-level security" in err_msg.lower():
                print(f"      [!] SUGERENCIA: Deshabilita RLS en Supabase SQL Editor para la tabla '{table_name}':")
                print(f"          ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;")

    print(f"  [✓] Tabla [{table_name}] completada: {len(inserted_records)} insertados con éxito, {failed_count} errores.")
    return inserted_records

# -----------------------------------------------------------------------------
# Ejecución Principal
# -----------------------------------------------------------------------------

def main():
    print("=" * 65)
    print("=== FASE 2: CARGA DE DATOS EN SUPABASE / POSTGRESQL ===")
    print("=" * 65)

    client = get_supabase_client()

    rfc_to_id = {}
    name_to_id = {}

    # 1. Pre-cargar empresas existentes en la BD para evitar duplicados si ya existen
    print("\n[1] Verificando empresas previamente registradas en Supabase...")
    try:
        existing_res = client.table('empresas').select('id, rfc, razon_social').execute()
        if existing_res.data:
            for item in existing_res.data:
                emp_id = item['id']
                if item.get('rfc'):
                    rfc_to_id[item['rfc']] = emp_id
                if item.get('razon_social'):
                    norm_n = normalize_name(item['razon_social'])
                    if norm_n:
                        name_to_id[norm_n] = emp_id
            print(f"  [i] {len(existing_res.data)} empresas existentes cargadas en memoria.")
    except Exception as e:
        print(f"  [!] Nota sobre empresas existentes: {e}")

    # 2. Cargar e Insertar EMPRESAS
    empresas_raw = load_json_file('empresas.json')
    empresas_cols = [
        'razon_social', 'rfc', 'tipo_empresa', 'numero_escritura', 'rpp',
        'fecha', 'notaria', 'domicilio_social', 'duracion', 'capital_total_fijo',
        'administrador_unico_gerente', 'apoderados', 'comisario', 'delegado',
        'asa_venta', 'numero_poder_revocacion', 'modificacion_estatutos',
        'afac_capi', 'observacion'
    ]

    empresas_to_insert = []
    for emp in empresas_raw:
        rfc = emp.get('rfc')
        norm_n = normalize_name(emp.get('razon_social'))
        if (rfc and rfc in rfc_to_id) or (norm_n and norm_n in name_to_id):
            continue

        # Filtrar solo columnas válidas para la tabla empresas
        clean_emp = {col: emp.get(col) for col in empresas_cols if col in emp}
        empresas_to_insert.append(clean_emp)

    print(f"  [i] Total empresas en JSON: {len(empresas_raw)}. Nuevas a insertar: {len(empresas_to_insert)}")
    inserted_empresas = batch_insert(client, 'empresas', empresas_to_insert)

    # Actualizar mapeo con los IDs generados por Supabase
    for emp in inserted_empresas:
        emp_id = emp.get('id')
        if not emp_id:
            continue
        if emp.get('rfc'):
            rfc_to_id[emp['rfc']] = emp_id
        if emp.get('razon_social'):
            norm_n = normalize_name(emp['razon_social'])
            if norm_n:
                name_to_id[norm_n] = emp_id

    # Función helper para obtener empresa_id de una fila dada
    def get_empresa_id(rfc, razon_social):
        if rfc and rfc in rfc_to_id:
            return rfc_to_id[rfc]
        norm_n = normalize_name(razon_social)
        if norm_n and norm_n in name_to_id:
            return name_to_id[norm_n]
        return None

    # 3. Cargar e Insertar SOCIOS
    socios_raw = load_json_file('socios.json')
    socios_to_insert = []
    unlinked_socios = 0

    for s in socios_raw:
        emp_id = get_empresa_id(s.get('rfc_empresa'), s.get('razon_social_empresa'))
        if emp_id:
            socios_to_insert.append({
                'empresa_id': emp_id,
                'nombre_socio': s.get('nombre_socio'),
                'porcentaje': s.get('porcentaje_participacion')
            })
        else:
            unlinked_socios += 1

    if unlinked_socios > 0:
        print(f"  [!] Advertencia: {unlinked_socios} socios no se pudieron asociar a ninguna empresa.")

    batch_insert(client, 'socios', socios_to_insert)

    # 4. Cargar e Insertar DOMICILIOS
    domicilios_raw = load_json_file('domicilios.json')
    domicilios_cols = ['razon_social', 'rfc', 'estado', 'municipio_delegacion', 'conocido', 'domicilio_fiscal', 'estatus']
    domicilios_to_insert = []

    for d in domicilios_raw:
        emp_id = get_empresa_id(d.get('rfc'), d.get('razon_social'))
        if emp_id:
            rec = {'empresa_id': emp_id}
            for col in domicilios_cols:
                rec[col] = d.get(col)
            domicilios_to_insert.append(rec)

    batch_insert(client, 'domicilios', domicilios_to_insert)

    # 5. Cargar e Insertar VENTAS
    ventas_raw = load_json_file('ventas.json')
    ventas_cols = [
        'razon_social', 'rfc', 'tipo_empresa', 'numero_escritura', 'rpp',
        'fecha', 'notaria', 'documento', 'domicilio_social', 'capital_total_fijo',
        'socios_capital_variable', 'administrador_unico_gerente', 'apoderados',
        'comisario', 'delegado', 'escrutador', 'observaciones'
    ]
    ventas_to_insert = []

    for v in ventas_raw:
        emp_id = get_empresa_id(v.get('rfc'), v.get('razon_social'))
        if emp_id:
            rec = {'empresa_id': emp_id}
            for col in ventas_cols:
                rec[col] = v.get(col)
            ventas_to_insert.append(rec)

    batch_insert(client, 'ventas', ventas_to_insert)

    # 6. Cargar e Insertar PODERES
    poderes_raw = load_json_file('poderes_revocacion.json') or load_json_file('poderes.json')
    poderes_cols = [
        'razon_social', 'rfc', 'tipo_empresa', 'numero_escritura', 'rpp',
        'fecha', 'notaria', 'documento', 'administrador_unico_gerente',
        'apoderados', 'delegado', 'observaciones'
    ]
    poderes_to_insert = []

    for p in poderes_raw:
        emp_id = get_empresa_id(p.get('rfc'), p.get('razon_social'))
        if emp_id:
            rec = {'empresa_id': emp_id}
            for col in poderes_cols:
                rec[col] = p.get(col)
            poderes_to_insert.append(rec)

    batch_insert(client, 'poderes', poderes_to_insert)

    # 7. Cargar e Insertar ESTATUTOS
    estatutos_raw = load_json_file('modificacion_estatutos.json') or load_json_file('estatutos.json')
    estatutos_cols = [
        'razon_social', 'rfc', 'numero_escritura', 'rpp', 'fecha',
        'notaria', 'documento', 'domicilio_social', 'capital_total_fijo',
        'administrador_unico_gerente', 'apoderados', 'comisario', 'delegado',
        'escrutador', 'observaciones'
    ]
    estatutos_to_insert = []

    for e in estatutos_raw:
        emp_id = get_empresa_id(e.get('rfc'), e.get('razon_social'))
        if emp_id:
            rec = {'empresa_id': emp_id}
            for col in estatutos_cols:
                rec[col] = e.get(col)
            estatutos_to_insert.append(rec)

    batch_insert(client, 'estatutos', estatutos_to_insert)

    print("=" * 65)
    print("=== PROCESO DE CARGA COMPLETADO CON ÉXITO ===")
    print("=" * 65)

if __name__ == '__main__':
    main()
