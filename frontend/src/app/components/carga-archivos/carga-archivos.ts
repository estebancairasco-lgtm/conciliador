import { Component, input, output, signal } from '@angular/core';

export interface ArchivosSeleccionados {
  facturas: File;
  contabilidad: File;
}

@Component({
  selector: 'app-carga-archivos',
  templateUrl: './carga-archivos.html',
})
export class CargaArchivos {
  readonly cargando = input(false);
  readonly procesar = output<ArchivosSeleccionados>();

  protected readonly facturas = signal<File | null>(null);
  protected readonly contabilidad = signal<File | null>(null);

  protected seleccionar(evento: Event, destino: 'facturas' | 'contabilidad'): void {
    const archivo = (evento.target as HTMLInputElement).files?.[0] ?? null;
    (destino === 'facturas' ? this.facturas : this.contabilidad).set(archivo);
  }

  protected enviar(): void {
    const facturas = this.facturas();
    const contabilidad = this.contabilidad();
    if (facturas && contabilidad) {
      this.procesar.emit({ facturas, contabilidad });
    }
  }
}
