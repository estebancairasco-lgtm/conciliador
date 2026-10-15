export type Estado = 'Correcta' | 'Con inconsistencia';

export interface Causa {
  codigo: string;
  descripcion: string;
  detalle: string;
}

export interface CausaResumen {
  codigo: string;
  descripcion: string;
  cantidad: number;
}

export interface Detalle {
  fila: number;
  id_factura: string;
  nit_proveedor: string;
  fecha_factura: string;
  concepto: string;
  base_gravable: number | null;
  tarifa_iva: number | null;
  valor_iva: number | null;
  iva_esperado: number | null;
  tarifa_retencion: number | null;
  valor_retencion: number | null;
  retencion_esperada: number | null;
  total_factura: number | null;
  total_esperado: number | null;
  estado_contable: string | null;
  valor_contabilizado: number | null;
  estado: Estado;
  causas: Causa[];
  advertencias: string[];
}

export interface Resumen {
  total_facturas: number;
  correctas: number;
  con_inconsistencia: number;
  porcentaje_inconsistencias: number;
  con_advertencias: number;
  total_registros_contables: number;
  causas: CausaResumen[];
  ids_contables_sin_factura: string[];
}

export interface Resultado {
  resumen: Resumen;
  detalle: Detalle[];
}
