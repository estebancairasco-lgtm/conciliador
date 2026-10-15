import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_URL } from '../config';
import { Resultado } from '../models/resultado';

@Injectable({ providedIn: 'root' })
export class ConciliadorService {
  private readonly http = inject(HttpClient);

  /** Envía los dos CSV al backend (multipart/form-data) y devuelve resumen y detalle. */
  conciliar(facturas: File, contabilidad: File): Observable<Resultado> {
    const datos = new FormData();
    datos.append('facturas', facturas);
    datos.append('contabilidad', contabilidad);
    return this.http.post<Resultado>(`${API_URL}/api/conciliar`, datos);
  }
}
