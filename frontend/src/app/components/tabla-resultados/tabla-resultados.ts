import { DecimalPipe } from '@angular/common';
import { Component, computed, input, signal } from '@angular/core';

import { Detalle } from '../../models/resultado';

type Filtro = 'Todos' | 'Correcta' | 'Con inconsistencia';

@Component({
  selector: 'app-tabla-resultados',
  imports: [DecimalPipe],
  templateUrl: './tabla-resultados.html',
})
export class TablaResultados {
  readonly detalle = input.required<Detalle[]>();

  protected readonly filtros: Filtro[] = ['Todos', 'Correcta', 'Con inconsistencia'];
  protected readonly filtro = signal<Filtro>('Todos');
  protected readonly busqueda = signal('');

  protected readonly filas = computed(() => {
    const texto = this.busqueda().trim().toLowerCase();
    return this.detalle().filter(
      (d) =>
        (this.filtro() === 'Todos' || d.estado === this.filtro()) &&
        (!texto || d.id_factura.toLowerCase().includes(texto)),
    );
  });

  protected cantidad(filtro: Filtro): number {
    return filtro === 'Todos'
      ? this.detalle().length
      : this.detalle().filter((d) => d.estado === filtro).length;
  }

  protected buscar(evento: Event): void {
    this.busqueda.set((evento.target as HTMLInputElement).value);
  }
}
