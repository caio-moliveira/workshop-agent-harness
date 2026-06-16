import type { Achado } from "../types";

export interface PontoGrafico {
  dimensao: string;
  serie: string;
  gap_pct: number;
}

const SERIES: Array<[string, keyof Achado]> = [
  ["tendência (6m)", "tendencia_gap_pct"],
  ["sazonal (2 anos)", "sazonal_gap_pct"],
];

// Espelha backend charts.spec_gaps: gap % vs meta por dimensão (tendência x sazonal).
// O SSE final traz `achados` (não o spec), então derivamos os pontos no cliente.
export function pontosDeAchados(achados: Achado[]): PontoGrafico[] {
  const pontos: PontoGrafico[] = [];
  for (const achado of achados) {
    for (const [rotulo, campo] of SERIES) {
      const valor = achado[campo];
      if (typeof valor === "number") {
        pontos.push({ dimensao: achado.dimensao, serie: rotulo, gap_pct: valor });
      }
    }
  }
  return pontos;
}
