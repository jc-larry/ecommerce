/**
 * Motor de colocación de prenda sobre vídeo en vivo (CU32 - Probador RA).
 *
 * El objetivo es el que pide el caso de uso: la clienta enciende la cámara y la prenda se
 * queda puesta sobre su cuerpo, acompañándola cuando se mueve, se inclina o gira. Eso
 * obliga a resolverlo **sin red**: un motor de difusión tarda segundos por imagen, así que
 * cualquier diseño que mande fotogramas al servidor produce justo lo que había antes, una
 * espera y una foto fija.
 *
 * Aquí la prenda se deforma en el propio navegador, fotograma a fotograma, sobre los
 * landmarks de pose. Las medidas de la prenda (dónde está su pecho, su bajo, sus mangas)
 * las calcula el backend una sola vez y llegan en un `GarmentRig`; este motor sólo las
 * proyecta sobre el cuerpo.
 *
 * Tres decisiones sostienen la calidad del resultado:
 *
 * 1. **Malla de triángulos, no un rectángulo.** El perfil de la prenda viene muestreado en
 *    18 filas con su ancho real, de modo que un peplum, una prenda acampanada o una blusa
 *    entallada conservan su silueta y la prenda se curva cuando la persona se inclina.
 * 2. **Escala anclada al pecho.** Todo se mide en anchos de pecho, no en píxeles ni en
 *    fracciones de la foto, así que la misma prenda cae bien de cerca y de lejos.
 * 3. **Recorte contra la silueta.** Si hay máscara de segmentación, la prenda se recorta
 *    contra el cuerpo: deja de "flotar" por fuera cuando el seguimiento titubea.
 */

export interface LiveLandmark {
  x: number;
  y: number;
  z?: number;
  visibility?: number;
}

export interface GarmentRigRow { y: number; cx: number; half: number; }

export interface GarmentRigData {
  cutout_url: string;
  width: number;
  height: number;
  kind: 'top' | 'outer' | 'dress' | 'bottom';
  sleeve: 'none' | 'short' | 'long';
  torso?: {
    rows: GarmentRigRow[];
    neck_y: number;
    shoulder_y: number;
    chest_y: number;
    hem_y: number;
    length_ratio: number;
    chest_half: number;
    shoulder_half: number;
  };
  sleeves?: { y0: number; y1: number; left: { x0: number; x1: number }; right: { x0: number; x1: number } } | null;
  bottom?: { waist: GarmentRigRow; hip: GarmentRigRow; crotch_y: number; hem: GarmentRigRow };
}

/** Rectángulo que ocupa el vídeo dentro del lienzo, en píxeles de pantalla. */
export interface VideoLayout {
  offsetX: number;
  offsetY: number;
  drawWidth: number;
  drawHeight: number;
}

export interface RenderOptions {
  /** Ajuste manual de talla del usuario (1 = medida calculada). */
  scale: number;
  offsetX: number;
  offsetY: number;
  opacity: number;
  /**
   * Redibuja el antebrazo por encima de la prenda cuando cruza por delante.
   *
   * El modo espejo no aparece aquí a propósito: se resuelve volteando por CSS el vídeo y
   * el lienzo a la vez, así que la geometría de este motor trabaja siempre sin voltear.
   */
  occludeForearms: boolean;
}

interface Point { x: number; y: number; }

const L_SHOULDER = 11, R_SHOULDER = 12;
const L_ELBOW = 13, R_ELBOW = 14;
const L_WRIST = 15, R_WRIST = 16;
const L_HIP = 23, R_HIP = 24;
const L_KNEE = 25, R_KNEE = 26;
const L_ANKLE = 27, R_ANKLE = 28;

/**
 * El ancho de pecho de una persona no es la distancia entre los puntos de hombro que
 * entrega la pose: esos caen en el acromion, por fuera de la caja torácica. Este factor
 * convierte una medida en la otra; sin él las prendas salían visiblemente anchas.
 */
const CHEST_OVER_SHOULDER_SPAN = 0.92;

/** Visibilidad para empezar a seguir el cuerpo y para dejar de seguirlo (histéresis). */
const ENTER_VISIBILITY = 0.30;
const EXIT_VISIBILITY = 0.15;
const HIP_ENTER_VISIBILITY = 0.35;
const HIP_EXIT_VISIBILITY = 0.18;

/**
 * Distancia hombro→cadera en anchos de hombros (entre puntos de pose). Sirve para estimar
 * las caderas cuando la persona está tan cerca que no entran en cuadro.
 *
 * Medido: 1.58 (mediana) en el vídeo de prueba y 1.55 sobre 737 personas de pie del conjunto
 * de entrenamiento (p10-p90: 1.41-1.81). Un primer valor supuesto de 1.3 dejaba la cadera
 * ~0.5 anchos de hombro demasiado arriba.
 */
const VIRTUAL_TORSO_OVER_SHOULDER_SPAN = 1.55;
/** Ancho entre las caderas de la pose respecto al de los hombros (medido: 0.57). */
const VIRTUAL_HIP_WIDTH = 0.6;

/** Cobertura mínima de la silueta sobre el torso para fiarse de ella al recortar. */
const MASK_MIN_TORSO_COVERAGE = 0.55;
/** Cuánto se ensancha la silueta (px del lienzo de la máscara) para no morder bordes. */
const MASK_DILATE_PX = 2;

/**
 * Copia de los landmarks con las caderas (23, 24) estimadas desde los hombros.
 *
 * La dirección "hacia abajo" sale de la perpendicular a la línea de hombros, de modo que
 * la prenda también se inclina cuando la persona se ladea.
 */
function withVirtualHips(landmarks: LiveLandmark[], aspect: number): LiveLandmark[] {
  const left = landmarks[L_SHOULDER];
  const right = landmarks[R_SHOULDER];
  // Los landmarks vienen normalizados por eje (x por el ancho, y por el alto), así que x e y
  // NO tienen la misma escala salvo en un vídeo cuadrado. Todo el cálculo se hace en un
  // espacio de unidades de alto (x·aspect, y) y se devuelve a normalizado al final.
  const dx = (left.x - right.x) * aspect;
  const dy = left.y - right.y;
  const span = Math.hypot(dx, dy);
  if (span < 1e-6) return landmarks;

  // Perpendicular a los hombros, orientada hacia abajo de la imagen (y crece hacia abajo).
  let downX = -dy / span;
  let downY = dx / span;
  if (downY < 0) { downX = -downX; downY = -downY; }

  const drop = span * VIRTUAL_TORSO_OVER_SHOULDER_SPAN;
  const midX = ((left.x + right.x) / 2) * aspect;
  const midY = (left.y + right.y) / 2;
  const half = VIRTUAL_HIP_WIDTH / 2;
  const visibility = Math.min(left.visibility ?? 1, right.visibility ?? 1);
  const z = ((left.z ?? 0) + (right.z ?? 0)) / 2;

  const points = landmarks.slice();
  points[L_HIP] = {
    x: (midX + dx * half + downX * drop) / aspect,
    y: midY + dy * half + downY * drop,
    z,
    visibility,
  };
  points[R_HIP] = {
    x: (midX - dx * half + downX * drop) / aspect,
    y: midY - dy * half + downY * drop,
    z,
    visibility,
  };
  return points;
}

/**
 * Filtro "One Euro": suaviza mucho cuando la persona está quieta y casi nada cuando se
 * mueve. Es lo que separa una prenda que se asienta en el cuerpo de una que tiembla.
 *
 * La media exponencial de factor fijo que había antes obligaba a elegir entre temblor
 * (factor alto) y retardo visible al moverse (factor bajo); este filtro decide solo,
 * usando la velocidad estimada del propio punto.
 */
class OneEuroFilter {
  private previous: number | null = null;
  private previousDerivative = 0;

  constructor(
    private readonly minCutoff = 1.0,
    private readonly beta = 0.08,
    private readonly derivativeCutoff = 1.0,
  ) {}

  private static alpha(cutoff: number, dt: number): number {
    const tau = 1 / (2 * Math.PI * cutoff);
    return 1 / (1 + tau / dt);
  }

  filter(value: number, dt: number): number {
    if (this.previous === null) {
      this.previous = value;
      return value;
    }
    const safeDt = Math.max(1 / 120, Math.min(0.2, dt));
    const derivative = (value - this.previous) / safeDt;
    const alphaD = OneEuroFilter.alpha(this.derivativeCutoff, safeDt);
    this.previousDerivative = this.previousDerivative + alphaD * (derivative - this.previousDerivative);

    const cutoff = this.minCutoff + this.beta * Math.abs(this.previousDerivative);
    const alpha = OneEuroFilter.alpha(cutoff, safeDt);
    const smoothed = this.previous + alpha * (value - this.previous);
    this.previous = smoothed;
    return smoothed;
  }

  reset(): void {
    this.previous = null;
    this.previousDerivative = 0;
  }
}

/** Suavizador de un juego completo de landmarks. */
export class PoseSmoother {
  private filters = new Map<number, { x: OneEuroFilter; y: OneEuroFilter; v: OneEuroFilter }>();
  private lastTimestamp = 0;

  smooth(landmarks: LiveLandmark[], timestampMs: number): LiveLandmark[] {
    const dt = this.lastTimestamp ? (timestampMs - this.lastTimestamp) / 1000 : 1 / 30;
    this.lastTimestamp = timestampMs;

    return landmarks.map((point, index) => {
      let entry = this.filters.get(index);
      if (!entry) {
        entry = {
          x: new OneEuroFilter(1.0, 0.08),
          y: new OneEuroFilter(1.0, 0.08),
          v: new OneEuroFilter(3.0, 0.05)
        };
        this.filters.set(index, entry);
      }
      return {
        x: entry.x.filter(point.x, dt),
        y: entry.y.filter(point.y, dt),
        z: point.z,
        visibility: entry.v.filter(point.visibility ?? 1, dt),
      };
    });
  }

  reset(): void {
    this.filters.clear();
    this.lastTimestamp = 0;
  }
}

export class LiveGarmentEngine {
  private rig: GarmentRigData | null = null;
  private cutout: HTMLImageElement | null = null;
  /** Lienzo intermedio: la prenda se compone aquí para poder recortarla contra el cuerpo. */
  private scratch: HTMLCanvasElement | null = null;

  setRig(rig: GarmentRigData | null, cutout: HTMLImageElement | null): void {
    this.rig = rig;
    this.cutout = cutout;
  }

  get ready(): boolean {
    return !!(this.rig && this.cutout && this.cutout.complete && this.cutout.naturalWidth > 0);
  }

  /** ¿Se ven los puntos que la prenda necesita para colocarse? (no modifica el estado) */
  hasUsableBody(landmarks: LiveLandmark[]): boolean {
    return this.evaluateBody(landmarks) !== null;
  }

  /**
   * Devuelve los landmarks listos para colocar la prenda, o `null` si no hay cuerpo.
   *
   * Dos reglas evitan que la prenda desaparezca sin que la persona se haya ido:
   *
   * 1. **Sólo los hombros son imprescindibles** en prendas superiores. Cuando la persona
   *    está cerca de la cámara las caderas quedan fuera de cuadro; antes eso apagaba la
   *    prenda aunque los hombros estuvieran perfectos. Ahora las caderas se estiman a
   *    partir de los hombros y de su inclinación.
   * 2. **Histéresis.** Se entra en "seguido" con visibilidad > 0.5 pero sólo se sale por
   *    debajo de 0.25, de modo que una visibilidad que oscila en torno a 0.5 no hace
   *    parpadear la prenda.
   */
  resolveBody(landmarks: LiveLandmark[]): LiveLandmark[] | null {
    const evaluated = this.evaluateBody(landmarks);
    this.tracking = evaluated !== null;
    if (evaluated === null) return null;
    this.hipsReal = evaluated.hipsReal;
    return evaluated.points;
  }

  private tracking = false;
  private hipsReal = true;
  /** Ancho/alto del vídeo mostrado; hace falta para estimar las caderas (ver `withVirtualHips`). */
  private aspect = 9 / 16;

  /** Lo actualiza el componente en cada fotograma con la proporción real del vídeo. */
  setVideoAspect(aspect: number): void {
    if (isFinite(aspect) && aspect > 0.2 && aspect < 5) this.aspect = aspect;
  }

  private evaluateBody(landmarks: LiveLandmark[]): { points: LiveLandmark[]; hipsReal: boolean } | null {
    if (!landmarks || landmarks.length < 33) return null;
    const vis = (index: number) => landmarks[index]?.visibility ?? 0;
    const bodyThreshold = this.tracking ? EXIT_VISIBILITY : ENTER_VISIBILITY;

    if (this.rig?.kind === 'bottom') {
      const ok = [L_HIP, R_HIP, L_KNEE, R_KNEE].every(index => vis(index) > bodyThreshold);
      return ok ? { points: landmarks, hipsReal: true } : null;
    }

    if (vis(L_SHOULDER) <= bodyThreshold || vis(R_SHOULDER) <= bodyThreshold) return null;

    // Las caderas reales sólo se usan si son fiables; con histéresis para no saltar entre
    // caderas reales y estimadas cuando la visibilidad oscila.
    const hipThreshold = this.hipsReal ? HIP_EXIT_VISIBILITY : HIP_ENTER_VISIBILITY;
    const hipsVisible = vis(L_HIP) > hipThreshold && vis(R_HIP) > hipThreshold;
    if (hipsVisible && this.hipsAreBelowShoulders(landmarks)) {
      return { points: landmarks, hipsReal: true };
    }
    return { points: withVirtualHips(landmarks, this.aspect), hipsReal: false };
  }

  /** Descarta caderas absurdas (por encima de los hombros): ocurre con la persona muy cerca. */
  private hipsAreBelowShoulders(landmarks: LiveLandmark[]): boolean {
    const shoulderY = (landmarks[L_SHOULDER].y + landmarks[R_SHOULDER].y) / 2;
    const hipY = (landmarks[L_HIP].y + landmarks[R_HIP].y) / 2;
    return hipY > shoulderY + 0.05;
  }

  /**
   * Dibuja la prenda sobre el cuerpo detectado.
   *
   * @param maskCanvas Silueta de la persona, si el detector la entrega. Cuando está, la
   *   prenda se recorta contra ella y deja de desbordarse por fuera del cuerpo.
   */
  render(
    ctx: CanvasRenderingContext2D,
    landmarks: LiveLandmark[],
    layout: VideoLayout,
    options: RenderOptions,
    video?: HTMLVideoElement | null,
    maskCanvas?: HTMLCanvasElement | null,
  ): void {
    const canvas = ctx.canvas;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!this.ready) return;
    this.setVideoAspect(layout.drawWidth / Math.max(1, layout.drawHeight));
    const body = this.resolveBody(landmarks);
    if (!body) return;
    // A partir de aquí `landmarks` son los del cuerpo resuelto (con caderas estimadas si
    // no se ven), no los crudos del detector.
    landmarks = body;

    const scratch = this.ensureScratch(canvas.width, canvas.height);
    const sctx = scratch.getContext('2d');
    if (!sctx) return;
    sctx.setTransform(1, 0, 0, 1, 0, 0);
    sctx.clearRect(0, 0, scratch.width, scratch.height);

    const toScreen = (index: number): Point => ({
      x: layout.offsetX + landmarks[index].x * layout.drawWidth + options.offsetX,
      y: layout.offsetY + landmarks[index].y * layout.drawHeight + options.offsetY,
    });

    if (this.rig!.kind === 'bottom') {
      this.renderBottom(sctx, toScreen, options);
    } else {
      this.renderTop(sctx, toScreen, landmarks, options);
    }

    // Recorte contra la silueta: lo que cae fuera del cuerpo se descarta.
    if (maskCanvas) {
      sctx.globalCompositeOperation = 'destination-in';
      sctx.drawImage(this.dilateMask(maskCanvas), layout.offsetX, layout.offsetY, layout.drawWidth, layout.drawHeight);
      sctx.globalCompositeOperation = 'source-over';
    }

    ctx.globalAlpha = options.opacity;
    ctx.drawImage(scratch, 0, 0);
    ctx.globalAlpha = 1;

    if (options.occludeForearms && video) {
      this.restoreForearms(ctx, landmarks, layout, options, video);
    }
  }

  /** Lienzo auxiliar de la silueta ensanchada. */
  private dilated: HTMLCanvasElement | null = null;

  /**
   * Ensancha la silueta unos píxeles dibujándola desplazada en 8 direcciones. Sin esto el
   * recorte muerde la prenda en el contorno del cuerpo (brazos, costados) porque la máscara
   * del detector es más ajustada que la ropa.
   */
  private dilateMask(mask: HTMLCanvasElement): HTMLCanvasElement {
    if (!this.dilated) this.dilated = document.createElement('canvas');
    const out = this.dilated;
    if (out.width !== mask.width || out.height !== mask.height) {
      out.width = mask.width;
      out.height = mask.height;
    }
    const dctx = out.getContext('2d');
    if (!dctx) return mask;
    dctx.clearRect(0, 0, out.width, out.height);
    const r = MASK_DILATE_PX;
    for (const [dx, dy] of [[0, 0], [r, 0], [-r, 0], [0, r], [0, -r], [r, r], [-r, r], [r, -r], [-r, -r]]) {
      dctx.drawImage(mask, dx, dy);
    }
    return out;
  }

  /**
   * ¿La silueta cubre lo bastante el torso como para fiarse de ella al recortar?
   *
   * Si el detector devuelve una máscara vacía o parcial (persona muy cerca, contraluz,
   * movimiento brusco), recortar contra ella borra la prenda entera aunque la pose sea
   * perfecta. En ese caso es preferible no recortar ese fotograma.
   *
   * @param values Probabilidades de persona por píxel, en el espacio de la máscara.
   * @param aspect Ancho/alto del vídeo, para pasar la distancia entre hombros a vertical.
   */
  static maskCoversTorso(
    values: ArrayLike<number>,
    maskWidth: number,
    maskHeight: number,
    landmarks: LiveLandmark[],
    aspect: number,
  ): boolean {
    const left = landmarks[L_SHOULDER];
    const right = landmarks[R_SHOULDER];
    if (!left || !right || maskWidth < 2 || maskHeight < 2) return false;

    const spanX = Math.abs(left.x - right.x);
    const centerX = (left.x + right.x) / 2;
    const topY = Math.min(left.y, right.y) + spanX * aspect * 0.15;
    const bottomY = Math.min(left.y, right.y) + spanX * aspect * 0.9;

    const x0 = Math.max(0, Math.floor((centerX - spanX * 0.35) * maskWidth));
    const x1 = Math.min(maskWidth - 1, Math.ceil((centerX + spanX * 0.35) * maskWidth));
    const y0 = Math.max(0, Math.floor(topY * maskHeight));
    const y1 = Math.min(maskHeight - 1, Math.ceil(bottomY * maskHeight));
    if (x1 <= x0 || y1 <= y0) return false;

    let inside = 0;
    let total = 0;
    for (let y = y0; y <= y1; y += 2) {
      for (let x = x0; x <= x1; x += 2) {
        total++;
        if (values[y * maskWidth + x] > 0.5) inside++;
      }
    }
    return total > 0 && inside / total >= MASK_MIN_TORSO_COVERAGE;
  }

  private ensureScratch(width: number, height: number): HTMLCanvasElement {
    if (!this.scratch) this.scratch = document.createElement('canvas');
    if (this.scratch.width !== width || this.scratch.height !== height) {
      this.scratch.width = width;
      this.scratch.height = height;
    }
    return this.scratch;
  }

  // ------------------------------------------------------------------
  // Prendas superiores, vestidos y abrigos
  // ------------------------------------------------------------------

  private renderTop(
    ctx: CanvasRenderingContext2D,
    toScreen: (index: number) => Point,
    landmarks: LiveLandmark[],
    options: RenderOptions,
  ): void {
    const torso = this.rig!.torso;
    if (!torso || torso.rows.length < 2) return;

    const shoulderLeft = toScreen(L_SHOULDER);
    const shoulderRight = toScreen(R_SHOULDER);
    const hipLeft = toScreen(L_HIP);
    const hipRight = toScreen(R_HIP);

    const shoulderMid = mid(shoulderLeft, shoulderRight);
    const hipMid = mid(hipLeft, hipRight);

    // Base horizontal tomada de la línea de hombros: así la prenda gira y se inclina con
    // el cuerpo en lugar de quedarse siempre horizontal.
    const across = normalize(sub(shoulderLeft, shoulderRight));
    const down = normalize(sub(hipMid, shoulderMid));
    if (!across || !down) return;

    const shoulderSpan = distance(shoulderLeft, shoulderRight);
    const bodyChestHalf = (shoulderSpan * CHEST_OVER_SHOULDER_SPAN * options.scale) / 2;
    if (bodyChestHalf < 4) return;

    // Píxeles de pantalla por unidad de "fracción de ancho del recorte".
    const pixelsPerUnit = bodyChestHalf / Math.max(0.01, torso.chest_half);
    const torsoLengthPx = resolveTorsoLength(
      this.rig!.kind,
      torso.length_ratio,
      bodyChestHalf,
      distance(shoulderMid, hipMid),
    );

    const spanY = Math.max(1e-4, torso.hem_y - torso.shoulder_y);
    const rows = torso.rows;

    // La costura de hombro de la prenda se apoya un poco por encima de la línea de
    // hombros de la pose: ese punto marca el acromion, y el tejido lo cubre.
    const anchor = add(shoulderMid, scale(down, -bodyChestHalf * 0.12));

    const vertices = rows.map(row => {
      const progress = (row.y - torso.shoulder_y) / spanY;
      const center = add(anchor, scale(down, progress * torsoLengthPx));
      const centerShift = scale(across, (row.cx - 0.5) * pixelsPerUnit);
      const rowCenter = add(center, centerShift);
      const halfPx = row.half * pixelsPerUnit;
      return {
        left: add(rowCenter, scale(across, halfPx)),
        right: add(rowCenter, scale(across, -halfPx)),
        source: {
          left: { x: (row.cx - row.half) * this.rig!.width, y: row.y * this.rig!.height },
          right: { x: (row.cx + row.half) * this.rig!.width, y: row.y * this.rig!.height },
        },
      };
    });

    // Mangas primero: la costura del hombro queda cubierta por el torso, que es como cae
    // la prenda de verdad.
    if (this.rig!.sleeve !== 'none' && this.rig!.sleeves) {
      this.renderSleeves(ctx, toScreen, pixelsPerUnit, options);
    }

    for (let i = 0; i < vertices.length - 1; i++) {
      const top = vertices[i];
      const bottom = vertices[i + 1];
      this.drawQuad(
        ctx,
        [top.source.left, top.source.right, bottom.source.right, bottom.source.left],
        [top.left, top.right, bottom.right, bottom.left],
      );
    }
  }

  /**
   * Reproyecta cada manga sobre el brazo.
   *
   * En la foto de producto la manga sale en diagonal hacia fuera; sobre el cuerpo tiene que
   * seguir el eje hombro→codo (manga corta) u hombro→codo→muñeca (manga larga). Sin esta
   * reproyección la manga se comprimía dentro del ancho del torso y producía las
   * "hombreras" cuadradas que se veían antes.
   */
  private renderSleeves(
    ctx: CanvasRenderingContext2D,
    toScreen: (index: number) => Point,
    pixelsPerUnit: number,
    options: RenderOptions,
  ): void {
    const sleeves = this.rig!.sleeves!;
    const long = this.rig!.sleeve === 'long';
    const rigWidth = this.rig!.width;
    const rigHeight = this.rig!.height;

    const segments: Array<{ box: { x0: number; x1: number }; shoulder: number; elbow: number; wrist: number }> = [
      // La caja izquierda del recorte corresponde al brazo que aparece a la izquierda de
      // la imagen, que en la pose es el hombro "derecho" del sujeto (índice 12).
      { box: sleeves.left, shoulder: R_SHOULDER, elbow: R_ELBOW, wrist: R_WRIST },
      { box: sleeves.right, shoulder: L_SHOULDER, elbow: L_ELBOW, wrist: L_WRIST },
    ];

    for (const segment of segments) {
      const shoulder = toScreen(segment.shoulder);
      const elbow = toScreen(segment.elbow);
      const wrist = toScreen(segment.wrist);

      const end = long ? wrist : lerp(shoulder, elbow, 0.5);
      const joint = long ? elbow : lerp(shoulder, end, 0.5);

      const boxWidth = (segment.box.x1 - segment.box.x0) * pixelsPerUnit;
      const halfWidth = Math.max(4, boxWidth / 2);

      // La manga se estrecha hacia el puño, como la propia manga y como el brazo.
      this.drawSleeveSegment(ctx, shoulder, joint, halfWidth, halfWidth * 0.82, {
        x0: segment.box.x0 * rigWidth,
        x1: segment.box.x1 * rigWidth,
        y0: sleeves.y0 * rigHeight,
        y1: (sleeves.y0 + (sleeves.y1 - sleeves.y0) * 0.5) * rigHeight,
      });
      this.drawSleeveSegment(ctx, joint, end, halfWidth * 0.82, halfWidth * 0.66, {
        x0: segment.box.x0 * rigWidth,
        x1: segment.box.x1 * rigWidth,
        y0: (sleeves.y0 + (sleeves.y1 - sleeves.y0) * 0.5) * rigHeight,
        y1: sleeves.y1 * rigHeight,
      });
    }
  }

  private drawSleeveSegment(
    ctx: CanvasRenderingContext2D,
    from: Point,
    to: Point,
    halfFrom: number,
    halfTo: number,
    source: { x0: number; x1: number; y0: number; y1: number },
  ): void {
    const axis = normalize(sub(to, from));
    if (!axis) return;
    const perpendicular = { x: -axis.y, y: axis.x };

    this.drawQuad(
      ctx,
      [
        { x: source.x0, y: source.y0 },
        { x: source.x1, y: source.y0 },
        { x: source.x1, y: source.y1 },
        { x: source.x0, y: source.y1 },
      ],
      [
        add(from, scale(perpendicular, -halfFrom)),
        add(from, scale(perpendicular, halfFrom)),
        add(to, scale(perpendicular, halfTo)),
        add(to, scale(perpendicular, -halfTo)),
      ],
    );
  }

  // ------------------------------------------------------------------
  // Prendas inferiores
  // ------------------------------------------------------------------

  private renderBottom(
    ctx: CanvasRenderingContext2D,
    toScreen: (index: number) => Point,
    options: RenderOptions,
  ): void {
    const bottom = this.rig!.bottom;
    if (!bottom) return;

    const hipLeft = toScreen(L_HIP);
    const hipRight = toScreen(R_HIP);
    const kneeLeft = toScreen(L_KNEE);
    const kneeRight = toScreen(R_KNEE);
    const ankleLeft = toScreen(L_ANKLE);
    const ankleRight = toScreen(R_ANKLE);

    const width = this.rig!.width;
    const height = this.rig!.height;
    const centerX = bottom.waist.cx * width;

    // Cada pernera se trata por separado, en dos tramos (cadera→rodilla, rodilla→tobillo),
    // para que el pantalón se doble cuando la persona flexiona las piernas.
    const legs = [
      { hip: hipRight, knee: kneeRight, ankle: ankleRight, x0: bottom.waist.cx - bottom.waist.half, x1: bottom.waist.cx },
      { hip: hipLeft, knee: kneeLeft, ankle: ankleLeft, x0: bottom.waist.cx, x1: bottom.waist.cx + bottom.waist.half },
    ];

    const waistY = bottom.waist.y * height;
    const crotchY = bottom.crotch_y * height;
    const hemY = bottom.hem.y * height;
    const hipSpan = distance(hipLeft, hipRight) * options.scale;
    const halfLeg = Math.max(6, hipSpan * 0.30);

    for (const leg of legs) {
      const axisUpper = normalize(sub(leg.knee, leg.hip));
      const axisLower = normalize(sub(leg.ankle, leg.knee));
      if (!axisUpper || !axisLower) continue;
      const perpUpper = { x: -axisUpper.y, y: axisUpper.x };
      const perpLower = { x: -axisLower.y, y: axisLower.x };

      this.drawQuad(
        ctx,
        [
          { x: leg.x0 * width, y: waistY },
          { x: leg.x1 * width, y: waistY },
          { x: leg.x1 * width, y: crotchY },
          { x: leg.x0 * width, y: crotchY },
        ],
        [
          add(leg.hip, scale(perpUpper, -halfLeg)),
          add(leg.hip, scale(perpUpper, halfLeg)),
          add(leg.knee, scale(perpUpper, halfLeg * 0.78)),
          add(leg.knee, scale(perpUpper, -halfLeg * 0.78)),
        ],
      );
      this.drawQuad(
        ctx,
        [
          { x: leg.x0 * width, y: crotchY },
          { x: leg.x1 * width, y: crotchY },
          { x: leg.x1 * width, y: hemY },
          { x: leg.x0 * width, y: hemY },
        ],
        [
          add(leg.knee, scale(perpLower, -halfLeg * 0.78)),
          add(leg.knee, scale(perpLower, halfLeg * 0.78)),
          add(leg.ankle, scale(perpLower, halfLeg * 0.66)),
          add(leg.ankle, scale(perpLower, -halfLeg * 0.66)),
        ],
      );
    }
  }

  // ------------------------------------------------------------------
  // Oclusión: el antebrazo que cruza por delante tapa la prenda
  // ------------------------------------------------------------------

  /**
   * Devuelve los píxeles reales del vídeo por encima de la prenda en la zona del antebrazo
   * cuando éste pasa por delante del torso.
   *
   * Sin esto, cruzarse de brazos delante del espejo dejaba los brazos escondidos debajo de
   * la ropa, que es el detalle que más delata que la prenda está "pegada" y no puesta. La
   * profundidad la da la `z` de la pose: es negativa hacia la cámara.
   */
  private restoreForearms(
    ctx: CanvasRenderingContext2D,
    landmarks: LiveLandmark[],
    layout: VideoLayout,
    options: RenderOptions,
    video: HTMLVideoElement,
  ): void {
    const torsoZ = ((landmarks[L_SHOULDER].z ?? 0) + (landmarks[R_SHOULDER].z ?? 0) +
      (landmarks[L_HIP].z ?? 0) + (landmarks[R_HIP].z ?? 0)) / 4;
    const shoulderSpan = Math.hypot(
      (landmarks[L_SHOULDER].x - landmarks[R_SHOULDER].x) * layout.drawWidth,
      (landmarks[L_SHOULDER].y - landmarks[R_SHOULDER].y) * layout.drawHeight,
    );
    const radius = Math.max(8, shoulderSpan * 0.16);

    for (const [elbowIndex, wristIndex] of [[L_ELBOW, L_WRIST], [R_ELBOW, R_WRIST]]) {
      const elbow = landmarks[elbowIndex];
      const wrist = landmarks[wristIndex];
      if ((elbow.visibility ?? 0) < 0.6 || (wrist.visibility ?? 0) < 0.6) continue;

      // Margen para no parpadear cuando el brazo está casi en el plano del torso.
      const armZ = ((elbow.z ?? 0) + (wrist.z ?? 0)) / 2;
      if (armZ > torsoZ - 0.06) continue;

      const a = {
        x: layout.offsetX + elbow.x * layout.drawWidth,
        y: layout.offsetY + elbow.y * layout.drawHeight,
      };
      const b = {
        x: layout.offsetX + wrist.x * layout.drawWidth,
        y: layout.offsetY + wrist.y * layout.drawHeight,
      };

      // Se recorta a la cápsula del antebrazo y se repinta el vídeo: el brazo vuelve a
      // quedar por delante de la prenda, con sus propios píxeles.
      ctx.save();
      ctx.clip(strokeToPath(a, b, radius));
      ctx.drawImage(video, layout.offsetX, layout.offsetY, layout.drawWidth, layout.drawHeight);
      ctx.restore();
    }
  }

  // ------------------------------------------------------------------
  // Rasterización
  // ------------------------------------------------------------------

  private drawQuad(ctx: CanvasRenderingContext2D, source: Point[], target: Point[]): void {
    this.drawTriangle(ctx, source[0], source[1], source[2], target[0], target[1], target[2]);
    this.drawTriangle(ctx, source[0], source[2], source[3], target[0], target[2], target[3]);
  }

  /**
   * Dibuja un triángulo de la textura con la transformación afín que lo lleva a su destino.
   *
   * Los triángulos se inflan medio píxel desde su centro antes de recortar: sin ese margen
   * quedaba una costura clara entre cada par de filas de la malla, porque el antialias de
   * dos recortes contiguos no llega a cubrir el borde común.
   */
  private drawTriangle(
    ctx: CanvasRenderingContext2D,
    s0: Point, s1: Point, s2: Point,
    d0: Point, d1: Point, d2: Point,
  ): void {
    const denominator = s0.x * (s2.y - s1.y) + s1.x * (s0.y - s2.y) + s2.x * (s1.y - s0.y);
    if (Math.abs(denominator) < 0.0001) return;

    const a = (d0.x * (s2.y - s1.y) + d1.x * (s0.y - s2.y) + d2.x * (s1.y - s0.y)) / denominator;
    const b = (d0.y * (s2.y - s1.y) + d1.y * (s0.y - s2.y) + d2.y * (s1.y - s0.y)) / denominator;
    const c = (d0.x * (s1.x - s2.x) + d1.x * (s2.x - s0.x) + d2.x * (s0.x - s1.x)) / denominator;
    const d = (d0.y * (s1.x - s2.x) + d1.y * (s2.x - s0.x) + d2.y * (s0.x - s1.x)) / denominator;
    const e = (d0.x * (s2.x * s1.y - s1.x * s2.y) + d1.x * (s0.x * s2.y - s2.x * s0.y) + d2.x * (s1.x * s0.y - s0.x * s1.y)) / denominator;
    const f = (d0.y * (s2.x * s1.y - s1.x * s2.y) + d1.y * (s0.x * s2.y - s2.x * s0.y) + d2.y * (s1.x * s0.y - s0.x * s1.y)) / denominator;

    const inflated = inflateTriangle(d0, d1, d2, 0.6);

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(inflated[0].x, inflated[0].y);
    ctx.lineTo(inflated[1].x, inflated[1].y);
    ctx.lineTo(inflated[2].x, inflated[2].y);
    ctx.closePath();
    ctx.clip();
    ctx.transform(a, b, c, d, e, f);
    ctx.drawImage(this.cutout!, 0, 0);
    ctx.restore();
  }
}

// ----------------------------------------------------------------------
// Utilidades geométricas
// ----------------------------------------------------------------------

/**
 * Decide cuánto baja la prenda por el cuerpo.
 *
 * El largo **no** puede salir sólo de la foto de producto. El rig lo mide en anchos de
 * pecho de la propia prenda, y esa cifra depende del encuadre: en el catálogo hay fotos
 * ajustadas a la prenda y otras recortadas o con zoom, y la misma clase de prenda pasaba
 * de 1.25 a 2.05 según la foto. Anclar a ciegas a esa cifra deja blusas por medio muslo.
 *
 * Lo que sí es fiable es el cuerpo: la distancia de hombros a caderas se mide en cada
 * fotograma. De ahí sale el largo objetivo por tipo de prenda. La medición de la foto se
 * conserva sólo para **acortar**: es lo que distingue un crop top de una camiseta normal,
 * y en eso sí es de fiar porque compara la prenda consigo misma.
 */
function resolveTorsoLength(
  kind: string,
  lengthRatio: number,
  bodyChestHalf: number,
  shoulderToHip: number,
): number {
  let target: number;
  switch (kind) {
    case 'dress':
      target = shoulderToHip * 1.85;   // hasta la rodilla
      break;
    case 'outer':
      target = shoulderToHip * 1.18;   // la chaqueta cubre la cadera
      break;
    default:
      target = shoulderToHip * 1.08;   // el bajo cae justo bajo la cadera
  }
  const measured = lengthRatio * bodyChestHalf * 2;
  // El suelo evita que una medición mala colapse la prenda sobre el pecho.
  return Math.min(target, Math.max(measured, shoulderToHip * 0.55));
}

function sub(a: Point, b: Point): Point { return { x: a.x - b.x, y: a.y - b.y }; }
function add(a: Point, b: Point): Point { return { x: a.x + b.x, y: a.y + b.y }; }
function scale(a: Point, k: number): Point { return { x: a.x * k, y: a.y * k }; }
function mid(a: Point, b: Point): Point { return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }; }
function lerp(a: Point, b: Point, t: number): Point {
  return { x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t };
}
function distance(a: Point, b: Point): number { return Math.hypot(a.x - b.x, a.y - b.y); }

function normalize(a: Point): Point | null {
  const length = Math.hypot(a.x, a.y);
  if (length < 1e-6) return null;
  return { x: a.x / length, y: a.y / length };
}

function inflateTriangle(d0: Point, d1: Point, d2: Point, amount: number): Point[] {
  const centroid = { x: (d0.x + d1.x + d2.x) / 3, y: (d0.y + d1.y + d2.y) / 3 };
  return [d0, d1, d2].map(point => {
    const direction = normalize(sub(point, centroid));
    return direction ? add(point, scale(direction, amount)) : point;
  });
}

/** Cápsula (rectángulo con extremos redondeados) alrededor del segmento a→b. */
function strokeToPath(a: Point, b: Point, radius: number): Path2D {
  const path = new Path2D();
  const axis = normalize(sub(b, a));
  if (!axis) {
    path.arc(a.x, a.y, radius, 0, Math.PI * 2);
    return path;
  }
  const angle = Math.atan2(axis.y, axis.x);
  path.arc(a.x, a.y, radius, angle + Math.PI / 2, angle - Math.PI / 2);
  path.arc(b.x, b.y, radius, angle - Math.PI / 2, angle + Math.PI / 2);
  path.closePath();
  return path;
}
