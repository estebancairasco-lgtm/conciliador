import { Component, computed, input } from '@angular/core';

import { Resumen } from '../../models/resultado';

@Component({
  selector: 'app-resumen-cards',
  templateUrl: './resumen-cards.html',
})
export class ResumenCards {
  readonly resumen = input.required<Resumen>();

  /** Solo las causas que realmente aparecieron en los archivos. */
  protected readonly causas = computed(() =>
    this.resumen().causas.filter((c) => c.cantidad > 0),
  );
}
