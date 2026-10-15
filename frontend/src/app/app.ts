import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { finalize } from 'rxjs';

import { ArchivosSeleccionados, CargaArchivos } from './components/carga-archivos/carga-archivos';
import { ResumenCards } from './components/resumen-cards/resumen-cards';
import { TablaResultados } from './components/tabla-resultados/tabla-resultados';
import { API_URL } from './config';
import { Resultado } from './models/resultado';
import { ConciliadorService } from './services/conciliador.service';

@Component({
  selector: 'app-root',
  imports: [CargaArchivos, ResumenCards, TablaResultados],
  templateUrl: './app.html',
})
export class App {
  private readonly servicio = inject(ConciliadorService);

  protected readonly cargando = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly resultado = signal<Resultado | null>(null);

  protected procesar(archivos: ArchivosSeleccionados): void {
    this.cargando.set(true);
    this.error.set(null);
    this.resultado.set(null);

    this.servicio
      .conciliar(archivos.facturas, archivos.contabilidad)
      .pipe(finalize(() => this.cargando.set(false)))
      .subscribe({
        next: (resultado) => this.resultado.set(resultado),
        error: (e: HttpErrorResponse) => this.error.set(this.mensajeDeError(e)),
      });
  }

  private mensajeDeError(e: HttpErrorResponse): string {
    if (e.status === 0) {
      return `No se pudo conectar con el backend en ${API_URL}. Verifica que esté corriendo.`;
    }
    const detalle = e.error?.detail;
    if (typeof detalle === 'string') {
      return detalle; // mensaje claro enviado por el backend (archivo inválido, columnas faltantes…)
    }
    return `Error ${e.status}: no se pudo procesar la solicitud.`;
  }
}
