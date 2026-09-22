import { Component, OnInit, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Subscription } from 'rxjs';
import {
  AnaliticaService,
  VirtualTryonResult,
  TryonSession,
  TryonItem,
  VTONGenerateResult,
  RemoveBackgroundResult,
  GarmentRig
} from '../analitica.service';
import { LiveGarmentEngine, PoseSmoother } from './live-garment-engine';
import { CatalogoService, Product, ProductVariant } from '../../paquete_catalogo_y_tiendas/catalogo.service';
import { ReservasService } from '../../paquete_reservas_y_citas/reservas.service';
import { VentasService } from '../../paquete_ventas_y_pagos/ventas.service';
import { FilesetResolver, PoseLandmarker } from '@mediapipe/tasks-vision';

/** Datos de los modelos reales del vestidor */
export interface RealModel {
  name: string;
  imageUrl: string;
  description: string;
}

const REAL_MODELS: RealModel[] = [
  { name: 'Sofía',   imageUrl: '/uploads/models/sofia.jpg',    description: 'Studio Fit' },
  { name: 'Valeria', imageUrl: '/uploads/models/valeria.jpg',  description: 'Haute Couture' },
  { name: 'Lin',     imageUrl: '/uploads/models/lin.jpg',      description: 'Casual Chic' },
  { name: 'Emma',    imageUrl: '/uploads/models/emma.jpg',     description: 'Athletic Studio' },
];

@Component({
  selector: 'app-virtual-tryon',
  templateUrl: './virtual-tryon.component.html',
  styleUrls: ['./virtual-tryon.component.css']
})
export class VirtualTryonComponent implements OnInit, OnDestroy {
  @ViewChild('videoPlayer') videoPlayer?: ElementRef<HTMLVideoElement>;
  @ViewChild('captureCanvas') captureCanvas?: ElementRef<HTMLCanvasElement>;
  @ViewChild('mirrorStage') mirrorStage?: ElementRef<HTMLDivElement>;
  @ViewChild('garmentOverlay') garmentOverlay?: ElementRef<HTMLCanvasElement>;

  // Sesión formal de vestidor (CU32)
  sessionToken: string = '';
  testedItems: TryonItem[] = [];

  // Catálogo de prendas y selección activa
  products: Product[] = [];
  selectedProduct: Product | null = null;
  selectedVariant: ProductVariant | null = null;
  availableColors: { id: number; name: string; hex: string; variantId: number }[] = [];

  // Sucursales para reserva en probador físico
  branches: any[] = [];
  selectedBranchId: number = 1;
  selectedDeliveryBranchId: number = 1;
  reservationDate: string = '';

  // Origen de silueta del cliente
  imageSource: 'model' | 'upload' | 'camera' | 'mannequin' = 'model';
  modelName: string = REAL_MODELS[0].name;
  uploadedPhotoUrl: string = '';
  // La vista puede usar una copia segmentada, pero el motor VTON siempre
  // recibe la foto original para conservar pose, rostro y proporciones.
  originalPersonImageUrl: string = REAL_MODELS[0].imageUrl;
  capturedSnapshotUrl: string = '';
  isCameraActive: boolean = false;
  cameraError: string = '';
  private mediaStream: MediaStream | null = null;

  // Rastreo y anclaje continuo de prenda sobre video en vivo (Pose/Torso Tracking)
  isTrackingActive: boolean = true;
  /** Vista en espejo: es como la clienta espera verse frente a un probador. */
  mirrorView: boolean = true;
  /** El antebrazo que pasa por delante del torso tapa la prenda. */
  occludeForearms: boolean = true;
  /** Estado del rig para poder avisar en pantalla mientras se mide la prenda. */
  rigStatus: 'idle' | 'loading' | 'ready' | 'failed' = 'idle';
  liveFps: number = 0;
  private trackingAnimationFrameId: number | null = null;
  private poseLandmarker: PoseLandmarker | null = null;
  private poseInitPromise: Promise<void> | null = null;
  private lastVideoTime: number = -1;
  private lastFrameStamp: number = 0;
  /** Ultima pose confiable: evita que una perdida breve de MediaPipe borre la prenda. */
  private lastReliableLandmarks: any[] | null = null;
  private lastReliablePoseAt: number = 0;
  private readonly poseHoldMs = 1000;
  private readonly poseFadeMs = 350;

  // Motor de colocacion en vivo: deforma el recorte de la prenda sobre los landmarks de
  // pose en cada fotograma, sin llamar al servidor.
  private liveEngine = new LiveGarmentEngine();
  private poseSmoother = new PoseSmoother();
  private garmentRig: GarmentRig | null = null;
  private garmentRigKey: string = '';
  private rigRequest: Subscription | null = null;
  /** Silueta de la persona; recorta la prenda para que no se salga del cuerpo. */
  private maskCanvas: HTMLCanvasElement | null = null;
  private maskUpdatedAt = 0;
  private readonly maskHoldMs = 750;

  // Delegado de MediaPipe en uso y sonda de respaldo (ver `watchPoseHealth`).
  private poseDelegate: 'GPU' | 'CPU' = 'GPU';
  private emptyPoseStreak = 0;
  private cpuProbe: PoseLandmarker | null = null;
  private cpuProbeBusy = false;
  private lastCpuProbeAt = 0;

  // Controles de superposición interactiva AR
  overlayScale: number = 1.0;
  overlayOffsetY: number = 0;
  overlayOffsetX: number = 0;
  overlayOpacity: number = 0.98;
  blendMode: 'normal' | 'multiply' | 'darken' = 'normal';
  showGuideGrid: boolean = false;
  showLandmarks: boolean = true;

  // Motor de Inteligencia Artificial (IDM-VTON / Difusión)
  selectedAIModel: 'IDM-VTON' | 'FASHN_AI' = 'IDM-VTON';
  isGeneratingVTON: boolean = false;
  vtonResult: VTONGenerateResult | null = null;
  activeViewMode: 'ar' | 'vton' | 'split' = 'ar';

  // Parámetros biométricos corporales y recomendación dinámica
  userHeight: number = 168;
  userWeight: number = 58;
  chestCm: number = 90;
  waistCm: number = 70;
  hipCm: number = 94;
  simulationResult: VirtualTryonResult | null = null;

  // Modelos reales del vestidor y remoción de fondo con IA
  realModels: RealModel[] = REAL_MODELS;
  selectedRealModel: RealModel | null = REAL_MODELS[0];
  isRemovingBg: boolean = false;

  // Landmarks anatómicos del backend
  garmentLandmarks: { [key: string]: any } | null = null;
  bodyLandmarks: { [key: string]: any } | null = null;

  // Modal selector visual de prendas
  showCatalogModal: boolean = false;
  catalogSearchTerm: string = '';
  selectedModalCategoryId: number | null = null;
  categories: any[] = [];

  // Estados generales de UI
  loading: boolean = false;
  successMsg: string = '';
  errorMsg: string = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private analiticaService: AnaliticaService,
    private catalogoService: CatalogoService,
    private reservasService: ReservasService,
    private ventasService: VentasService
  ) {}

  resolveImg(url?: string | null): string {
    return this.catalogoService.resolveImageUrl(url);
  }

  // Talla 100% dinámica calculada según medidas corporales (no fija en S)
  get calculatedSize(): string {
    if (this.chestCm < 86) return 'XS';
    if (this.chestCm <= 92) return 'S';
    if (this.chestCm <= 100) return 'M';
    if (this.chestCm <= 108) return 'L';
    if (this.chestCm <= 116) return 'XL';
    return 'XXL';
  }

  get fitScaleFactor(): number {
    const sizeMap: { [key: string]: number } = {
      'XS': 0.94, 'S': 0.98, 'M': 1.04, 'L': 1.12, 'XL': 1.20, 'XXL': 1.28
    };
    return (sizeMap[this.calculatedSize] || 1.0) * this.overlayScale;
  }

  get fitAssessment(): string {
    const s = this.calculatedSize;
    if (s === 'XS') return 'Corte ceñido estilizado';
    if (s === 'S') return 'Ajuste slim fit elegante';
    if (s === 'M') return 'Ajuste regular estándar';
    if (s === 'L') return 'Ajuste relajado con caída';
    return 'Corte confort holgado';
  }

  get hasPersonPhoto(): boolean {
    return !!this.getActivePersonImageUrl();
  }

  get isDressOrOnePiece(): boolean {
    if (!this.selectedProduct) return false;
    const cat = (this.selectedProduct.category?.name || '').toLowerCase();
    const name = (this.selectedProduct.name || '').toLowerCase();
    return cat.includes('vestido') || cat.includes('enterizo') || cat.includes('mono') ||
           cat.includes('pieza') || name.includes('vestido') || name.includes('kaftan') || name.includes('caftan');
  }

  get isBottom(): boolean {
    if (!this.selectedProduct) return false;
    const cat = (this.selectedProduct.category?.name || '').toLowerCase();
    const name = (this.selectedProduct.name || '').toLowerCase();
    return cat.includes('pantalon') || cat.includes('pantalón') || cat.includes('falda') ||
           cat.includes('jean') || cat.includes('short') || name.includes('pantalon') || name.includes('falda');
  }

  onMeasurementsChanged(): void {
    this.runSimulation();
  }

  removeTestedItem(item: TryonItem, e?: Event): void {
    if (e) e.stopPropagation();
    this.testedItems = this.testedItems.filter(x => x.id !== item.id);
  }

  ngOnInit(): void {
    this.reservationDate = this.getDefaultReservationDate();
    this.initSession();
    this.loadBranches();
    this.loadProducts();
  }

  ngOnDestroy(): void {
    this.stopWebcam();
    this.rigRequest?.unsubscribe();
  }

  // 1. Inicialización y trazabilidad de sesión (CU32)
  initSession(): void {
    const savedToken = localStorage.getItem('fs_tryon_session_token');
    if (savedToken) {
      this.sessionToken = savedToken;
      this.loadTestedItems();
    } else {
      this.analiticaService.startTryonSession('WEB').subscribe({
        next: (res: TryonSession) => {
          this.sessionToken = res.session_token;
          localStorage.setItem('fs_tryon_session_token', this.sessionToken);
        },
        error: () => {
          // Token de respaldo en caso de desconexión
          this.sessionToken = 'sess_' + Math.random().toString(36).substring(2, 12);
        }
      });
    }
  }

  loadTestedItems(): void {
    if (!this.sessionToken) return;
    this.analiticaService.getSessionTestedItems(this.sessionToken).subscribe({
      next: (items: TryonItem[]) => {
        this.testedItems = items;
      },
      error: () => {}
    });
  }

  loadBranches(): void {
    this.catalogoService.getBranches().subscribe({
      next: (b: any[]) => {
        this.branches = b.filter(branch => (branch.city || '').toLowerCase().includes('santa cruz'));
        if (this.branches.length > 0) {
          this.selectedBranchId = this.branches[0].id;
          this.selectedDeliveryBranchId = this.branches[0].id;
        }
      },
      error: () => {}
    });
  }

  loadProducts(): void {
    this.catalogoService.getCategories().subscribe({
      next: (cats: any[]) => { this.categories = cats; },
      error: () => {}
    });
    this.catalogoService.getProducts().subscribe({
      next: (prods: Product[]) => {
        this.products = prods;
        this.route.queryParams.subscribe(params => {
          if (params['productId']) {
            const p = this.products.find(x => x.id === +params['productId']);
            if (p) this.selectedProduct = p;
          }
          if (!this.selectedProduct && this.products.length > 0) {
            this.selectedProduct = this.products[0];
          }
          if (this.selectedProduct) {
            this.setupProductVariants(params['variantId'] ? +params['variantId'] : undefined);
          }
        });
      },
      error: () => {}
    });
  }

  get filteredModalProducts(): Product[] {
    const q = (this.catalogSearchTerm || '').trim().toLowerCase();
    return this.products.filter(p => {
      const matchName = !q || (p.name || '').toLowerCase().includes(q) || (p.category?.name || '').toLowerCase().includes(q);
      const matchCat = this.selectedModalCategoryId === null || p.category_id === this.selectedModalCategoryId;
      return matchName && matchCat;
    });
  }

  selectProduct(p: Product): void {
    this.selectedProduct = p;
    this.vtonResult = null;
    this.activeViewMode = 'ar';
    this.showCatalogModal = false;
    this.resetOverlay();
    this.setupProductVariants();
  }

  selectTestedItem(item: TryonItem): void {
    const p = this.products.find(x => x.id === item.product_id);
    if (p) {
      this.selectedProduct = p;
      this.vtonResult = null;
      this.activeViewMode = 'ar';
      this.resetOverlay();
      this.setupProductVariants(item.variant_id);
    }
  }

  setupProductVariants(preferredVariantId?: number): void {
    if (!this.selectedProduct) return;
    const variants = this.selectedProduct.variants || [];
    this.availableColors = [];

    const seenColors = new Set<string>();
    for (const v of variants) {
      if (v.color && !seenColors.has(v.color.name)) {
        seenColors.add(v.color.name);
        this.availableColors.push({
          id: v.color.id,
          name: v.color.name,
          hex: v.color.hex_code || '#706361',
          variantId: v.id
        });
      }
    }

    if (preferredVariantId) {
      const match = variants.find(v => v.id === preferredVariantId);
      this.selectedVariant = match || (variants.length > 0 ? variants[0] : null);
    } else {
      this.selectedVariant = variants.length > 0 ? variants[0] : null;
    }

    // Registrar automáticamente la prueba de la prenda en la sesión activa
    this.recordTestedItem();
    this.loadGarmentForCamera();
    this.runSimulation();
  }

  // Cambio de variante de color con un tap (RF47)
  selectColorVariant(col: { id: number; name: string; hex: string; variantId: number }): void {
    if (!this.selectedProduct) return;
    const match = (this.selectedProduct.variants || []).find(v => v.id === col.variantId);
    if (match) {
      this.selectedVariant = match;
      this.vtonResult = null;
      this.activeViewMode = 'ar';
      this.recordTestedItem();
      // El color cambia la foto de la prenda, así que hay que volver a medirla.
      this.loadGarmentForCamera();
    }
  }

  recordTestedItem(): void {
    if (!this.selectedProduct || !this.sessionToken) return;
    this.analiticaService.logTestedItem({
      session_token: this.sessionToken,
      product_id: this.selectedProduct.id,
      variant_id: this.selectedVariant?.id,
      tested_size: this.selectedVariant?.size?.name || 'M',
      fit_feedback: 'Visualización activa en vestidor RA',
    }).subscribe({
      next: (item: TryonItem) => {
        const idx = this.testedItems.findIndex(x => x.product_id === item.product_id && x.variant_id === item.variant_id);
        if (idx >= 0) {
          this.testedItems[idx] = item;
        } else {
          this.testedItems.unshift(item);
        }
      },
      error: () => {}
    });
  }

  // 2. Control de Origen de Silueta (Maniquí / Cámara / Subida)
  useMannequin(): void {
    this.stopWebcam();
    this.imageSource = 'mannequin';
    this.originalPersonImageUrl = '';
    this.uploadedPhotoUrl = '';
    this.selectedRealModel = null;
    this.vtonResult = null;
    this.activeViewMode = 'ar';
  }

  useModel(): void {
    this.stopWebcam();
    if (!this.selectedRealModel && this.realModels.length > 0) {
      this.selectRealModel(this.realModels[0]);
      return;
    }
    this.imageSource = 'model';
    this.vtonResult = null;
    this.activeViewMode = 'ar';
    this.runSimulation();
  }

  onPhotoUploaded(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files[0]) {
      const file = input.files[0];
      if (!file.type.startsWith('image/') || file.size > 15 * 1024 * 1024) {
        this.errorMsg = 'Selecciona una imagen válida de máximo 15 MB.';
        input.value = '';
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        const rawImageUrl = reader.result as string;
        this.imageSource = 'upload';
        this.selectedRealModel = null;
        this.originalPersonImageUrl = rawImageUrl;
        // Se muestra inmediatamente la foto original; la versión segmentada
        // solo sustituye esta vista cuando el endpoint termina.
        this.uploadedPhotoUrl = rawImageUrl;
        this.vtonResult = null;
        this.activeViewMode = 'ar';
        this.stopWebcam();

        // Remover fondo automáticamente con IA (rembg u2net)
        this.isRemovingBg = true;
        this.successMsg = '';
        this.errorMsg = '';
        this.analiticaService.removeBackground(rawImageUrl).subscribe({
          next: (res: RemoveBackgroundResult) => {
            this.uploadedPhotoUrl = res.processed_image_url;
            this.isRemovingBg = false;
            const maskPercent = Math.round((res.mask_confidence || 0) * 100);
            const posePercent = Math.round((res.pose_confidence || 0) * 100);
            this.successMsg = res.mask_reliable && res.pose_valid
              ? `Silueta y postura detectadas: máscara ${maskPercent}%, pose ${posePercent}%. Ajuste anatómico activado.`
              : `Detección parcial: máscara ${maskPercent}%, pose ${posePercent}%. Se aplicará un ajuste conservador para evitar que la prenda salga del cuerpo.`;
            this.runSimulation();
            this.generatePhotorealisticVTON();
          },
          error: () => {
            // Fallback: usar imagen original sin segmentar
            this.uploadedPhotoUrl = rawImageUrl;
            this.isRemovingBg = false;
            this.runSimulation();
            this.generatePhotorealisticVTON();
          }
        });
      };
      reader.readAsDataURL(file);
      input.value = '';
    }
  }

  selectRealModel(model: RealModel): void {
    this.selectedRealModel = model;
    this.stopWebcam();
    this.vtonResult = null;
    this.activeViewMode = 'ar';
    this.imageSource = 'model';
    this.uploadedPhotoUrl = this.resolveImg(model.imageUrl);
    this.originalPersonImageUrl = this.resolveImg(model.imageUrl);
    this.modelName = model.name;
    this.runSimulation();
  }

  async startWebcam(): Promise<void> {
    this.cameraError = '';
    this.imageSource = 'camera';
    this.vtonResult = null;
    this.activeViewMode = 'ar';
    try {
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 720 },
          height: { ideal: 1080 }
        }
      });
      await this.ensurePoseLandmarker();
      this.isCameraActive = true;
      setTimeout(() => {
        if (this.videoPlayer && this.videoPlayer.nativeElement) {
          this.videoPlayer.nativeElement.srcObject = this.mediaStream;
          this.videoPlayer.nativeElement.play();
          this.startLiveVideoTracking();
        }
      }, 150);
    } catch (err: any) {
      this.cameraError = 'No se pudo activar la cámara web. Asegúrate de otorgar permisos o sube una fotografía.';
      this.isCameraActive = false;
      this.imageSource = 'mannequin';
    }
  }

  /**
   * Bucle del probador en vivo: una detección de pose por fotograma de vídeo y un
   * repintado de la prenda deformada sobre el cuerpo. Todo ocurre en el navegador; no hay
   * ninguna llamada al servidor dentro de este bucle.
   */
  startLiveVideoTracking(): void {
    if (this.trackingAnimationFrameId !== null) {
      cancelAnimationFrame(this.trackingAnimationFrameId);
    }
    const trackLoop = () => {
      if (!this.isCameraActive || !this.videoPlayer?.nativeElement) {
        return;
      }
      const video = this.videoPlayer.nativeElement;
      if (video.readyState >= 2 && video.currentTime !== this.lastVideoTime && this.poseLandmarker) {
        this.lastVideoTime = video.currentTime;
        const now = performance.now();
        if (this.lastFrameStamp) {
          const instant = 1000 / Math.max(1, now - this.lastFrameStamp);
          this.liveFps = Math.round(this.liveFps * 0.9 + instant * 0.1);
        }
        this.lastFrameStamp = now;

        try {
          const result = this.poseLandmarker.detectForVideo(video, now);
          this.watchPoseHealth(video, (result?.landmarks?.length ?? 0) > 0, now);
          this.renderTrackedOrHeldPose(video, result, now);
        } catch (error) {
          // Un fallo aislado del detector no debe detener requestAnimationFrame ni hacer
          // desaparecer la prenda. El siguiente fotograma intentara recuperar la pose.
          console.warn('MediaPipe no pudo procesar un fotograma; se conserva la ultima pose.', error);
          this.renderTrackedOrHeldPose(video, null, now);
        }
      }
      this.trackingAnimationFrameId = requestAnimationFrame(trackLoop);
    };

    this.trackingAnimationFrameId = requestAnimationFrame(trackLoop);
  }

  /**
   * Usa la pose nueva cuando es completa. Si MediaPipe pierde uno o varios fotogramas,
   * conserva la ultima pose durante 750 ms y luego desvanece suavemente durante 350 ms.
   * Asi no hay parpadeo por motion blur, pero tampoco queda una prenda congelada si la
   * persona abandona la camara.
   */
  private renderTrackedOrHeldPose(video: HTMLVideoElement, result: any, now: number): void {
    if (!this.isTrackingActive) {
      this.lastReliableLandmarks = null;
      this.closeSegmentationMasks(result);
      this.clearGarmentCanvas();
      return;
    }

    this.liveEngine.setVideoAspect(video.videoWidth / Math.max(1, video.videoHeight));
    if (result?.landmarks?.length > 0) {
      const smoothed = this.poseSmoother.smooth(result.landmarks[0], now);
      if (this.liveEngine.hasUsableBody(smoothed)) {
        this.lastReliableLandmarks = smoothed.map(point => ({ ...point }));
        this.lastReliablePoseAt = now;
        this.paintLiveFrame(video, smoothed, result);
        return;
      }
    }

    const ageMs = now - this.lastReliablePoseAt;
    const maxGraceMs = this.poseHoldMs + this.poseFadeMs;
    if (this.lastReliableLandmarks && ageMs <= maxGraceMs) {
      const opacityFactor = ageMs <= this.poseHoldMs
        ? 1
        : Math.max(0, 1 - (ageMs - this.poseHoldMs) / this.poseFadeMs);
      this.paintLiveFrame(video, this.lastReliableLandmarks, result, opacityFactor);
      return;
    }

    this.lastReliableLandmarks = null;
    this.lastReliablePoseAt = 0;
    this.poseSmoother.reset();
    this.closeSegmentationMasks(result);
    this.clearGarmentCanvas();
  }

  /** Coloca la prenda del fotograma actual sobre el cuerpo detectado. */
  private paintLiveFrame(
    video: HTMLVideoElement,
    landmarks: any[],
    result: any,
    opacityFactor: number = 1,
  ): void {
    const canvas = this.garmentOverlay?.nativeElement;
    const stage = this.mirrorStage?.nativeElement;
    if (!canvas || !stage) return;

    const width = stage.clientWidth;
    const height = stage.clientHeight;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // El vídeo va en `object-fit: contain`, así que hay bandas a los lados o arriba: los
    // landmarks vienen en fracciones del vídeo, no del lienzo, y hay que mapearlos.
    const videoScale = Math.min(width / video.videoWidth, height / video.videoHeight);
    const drawWidth = video.videoWidth * videoScale;
    const drawHeight = video.videoHeight * videoScale;

    this.liveEngine.render(
      ctx,
      landmarks,
      {
        offsetX: (width - drawWidth) / 2,
        offsetY: (height - drawHeight) / 2,
        drawWidth,
        drawHeight,
      },
      {
        scale: this.fitScaleFactor,
        offsetX: this.overlayOffsetX,
        offsetY: this.overlayOffsetY,
        opacity: this.overlayOpacity * opacityFactor,
        occludeForearms: this.occludeForearms,
      },
      video,
      this.pickMask(result, landmarks, video),
    );

    // Las máscaras de MediaPipe retienen memoria de GPU hasta que se cierran: sin esto se
    // acumularía una por fotograma y el probador acabaría ahogando la pestaña.
    this.closeSegmentationMasks(result);
  }

  /**
   * Silueta para recortar la prenda: la de este fotograma si es fiable; si no, la última
   * buena durante `maskHoldMs`; pasado ese tiempo, ninguna (mejor sin recorte que sin prenda).
   */
  private pickMask(result: any, landmarks: any[], video: HTMLVideoElement): HTMLCanvasElement | null {
    const aspect = video.videoWidth / Math.max(1, video.videoHeight);
    const fresh = this.buildMaskCanvas(result, landmarks, aspect);
    const now = performance.now();
    if (fresh) {
      this.maskUpdatedAt = now;
      return fresh;
    }
    return this.maskCanvas && now - this.maskUpdatedAt <= this.maskHoldMs ? this.maskCanvas : null;
  }

  private closeSegmentationMasks(result: any): void {
    for (const mask of (result?.segmentationMasks ?? [])) mask.close?.();
  }

  /**
   * Convierte la máscara de segmentación de MediaPipe en un lienzo utilizable.
   *
   * Recortar la prenda contra la silueta es lo que evita que se vea flotando por fuera del
   * cuerpo cuando el seguimiento titubea o la persona se gira de perfil.
   */
  private buildMaskCanvas(result: any, landmarks: any[], aspect: number): HTMLCanvasElement | null {
    const masks = result?.segmentationMasks;
    if (!masks || masks.length === 0) return null;
    const mask = masks[0];
    const values: Float32Array | undefined = mask.getAsFloat32Array?.();
    if (!values) return null;

    // Una máscara vacía o parcial recortaría la prenda entera: si no cubre el torso se
    // descarta sin tocar la última buena, que sigue en `maskCanvas`.
    if (!LiveGarmentEngine.maskCoversTorso(values, mask.width, mask.height, landmarks, aspect)) {
      return null;
    }

    if (!this.maskCanvas) this.maskCanvas = document.createElement('canvas');
    const canvas = this.maskCanvas;
    if (canvas.width !== mask.width || canvas.height !== mask.height) {
      canvas.width = mask.width;
      canvas.height = mask.height;
    }
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;

    const image = ctx.createImageData(mask.width, mask.height);
    for (let i = 0; i < values.length; i++) {
      image.data[i * 4 + 3] = values[i] > 0.5 ? 255 : 0;
    }
    ctx.putImageData(image, 0, 0);
    return canvas;
  }

  /** Crea un detector de pose con el modelo local y los umbrales del plan (0.55). */
  private async createPoseLandmarker(delegate: 'GPU' | 'CPU'): Promise<PoseLandmarker> {
    const vision = await FilesetResolver.forVisionTasks('/assets/mediapipe/wasm');
    return PoseLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: '/assets/mediapipe/pose_landmarker_lite.task',
        delegate
      },
      runningMode: 'VIDEO',
      numPoses: 1,
      // La mascara de silueta recorta la prenda contra el cuerpo.
      outputSegmentationMasks: true,
      minPoseDetectionConfidence: 0.40,
      minPosePresenceConfidence: 0.40,
      minTrackingConfidence: 0.40
    });
  }

  private readStoredDelegate(): 'GPU' | 'CPU' | null {
    try {
      const value = sessionStorage.getItem('tryon_pose_delegate');
      return value === 'CPU' || value === 'GPU' ? value : null;
    } catch { return null; }
  }

  private storeDelegate(delegate: 'GPU' | 'CPU'): void {
    try { sessionStorage.setItem('tryon_pose_delegate', delegate); } catch { /* sin almacenamiento */ }
  }

  /**
   * Vigila que el delegado GPU no falle en silencio.
   *
   * Hay equipos donde la GPU se crea sin error pero nunca devuelve una pose: la prenda no
   * aparece jamas y no hay nada que capturar. Si llevamos ~2 s sin pose, se prueba el mismo
   * fotograma en un detector CPU; si este si ve a la persona, se cambia a CPU de forma
   * permanente. Si tampoco ve a nadie, es que no hay nadie delante y no se hace nada.
   */
  private watchPoseHealth(video: HTMLVideoElement, hasPose: boolean, now: number): void {
    if (hasPose) {
      this.emptyPoseStreak = 0;
      if (this.cpuProbe) { this.cpuProbe.close(); this.cpuProbe = null; }
      return;
    }
    this.emptyPoseStreak++;
    if (this.poseDelegate !== 'GPU' || this.emptyPoseStreak < 60 || this.cpuProbeBusy) return;
    if (now - this.lastCpuProbeAt < 4000) return;

    this.cpuProbeBusy = true;
    this.lastCpuProbeAt = now;
    (async () => {
      try {
        if (!this.cpuProbe) this.cpuProbe = await this.createPoseLandmarker('CPU');
        const result = this.cpuProbe.detectForVideo(video, performance.now());
        const found = (result?.landmarks?.length ?? 0) > 0;
        this.closeSegmentationMasks(result);
        if (found) {
          console.warn('La GPU de MediaPipe no detecta pero la CPU si: se cambia a CPU.');
          this.poseLandmarker?.close();
          this.poseLandmarker = this.cpuProbe;
          this.cpuProbe = null;
          this.poseDelegate = 'CPU';
          this.storeDelegate('CPU');
          this.poseSmoother.reset();
        }
      } catch (error) {
        console.warn('No se pudo probar el respaldo CPU de MediaPipe.', error);
      } finally {
        this.cpuProbeBusy = false;
      }
    })();
  }

  private async ensurePoseLandmarker(): Promise<void> {
    if (this.poseLandmarker) return;
    if (this.poseInitPromise) return this.poseInitPromise;
    this.poseInitPromise = (async () => {
      // Si en una sesion anterior la GPU resulto no funcionar, se arranca directo en CPU.
      const preferred: 'GPU' | 'CPU' = this.readStoredDelegate() ?? 'GPU';
      try {
        this.poseLandmarker = await this.createPoseLandmarker(preferred);
        this.poseDelegate = preferred;
      } catch (gpuError) {
        console.warn('MediaPipe GPU no disponible; se activa el delegado CPU.', gpuError);
        this.poseLandmarker = await this.createPoseLandmarker('CPU');
        this.poseDelegate = 'CPU';
      }
    })();
    try {
      await this.poseInitPromise;
    } catch (error) {
      this.poseInitPromise = null;
      throw error;
    }
  }

  /**
   * Pide al backend el rig de la prenda seleccionada y carga su recorte.
   *
   * El rig trae la prenda ya separada del fondo y **medida**: dónde caen su pecho, su bajo
   * y sus mangas. Antes esto se resolvía en el navegador volviendo transparente todo lo
   * casi blanco y anclando a fracciones fijas de la imagen, lo que fallaba en los dos
   * casos más comunes del catálogo (prenda blanca sobre fondo blanco, y fotos con mucho
   * aire alrededor). Se pide una vez por prenda y el servidor lo tiene cacheado.
   */
  private loadGarmentForCamera(): void {
    const product = this.selectedProduct;
    if (!product) return;

    // Las prendas multicolor traen una galería por color: se mide la foto del color
    // elegido, no la primera de la lista, o el recorte no correspondería a lo que se ve.
    const images = product.images || [];
    const colorId = this.selectedVariant?.color_id;
    const forColor = colorId ? images.filter(i => i.color_id === colorId) : [];
    const pool = forColor.length ? forColor : images;
    const raw = (pool.find(i => i.is_primary) || pool[0])?.image_url || '';
    const key = `${product.id}|${raw}`;
    if (key === this.garmentRigKey) return;

    this.garmentRigKey = key;
    this.rigStatus = 'loading';
    this.rigRequest?.unsubscribe();
    this.rigRequest = this.analiticaService.getGarmentRig(product.id, raw || undefined).subscribe({
      next: (rig) => {
        this.garmentRig = rig;
        const image = new Image();
        image.crossOrigin = 'anonymous';
        image.onload = () => {
          this.liveEngine.setRig(rig as any, image);
          this.rigStatus = 'ready';
        };
        image.onerror = () => {
          this.liveEngine.setRig(null, null);
          this.rigStatus = 'failed';
        };
        image.src = this.resolveImg(rig.cutout_url);
      },
      error: () => {
        this.garmentRig = null;
        this.liveEngine.setRig(null, null);
        this.rigStatus = 'failed';
      }
    });
  }


  private clearGarmentCanvas(): void {
    const canvas = this.garmentOverlay?.nativeElement;
    canvas?.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height);
  }

  stopWebcam(): void {
    if (this.trackingAnimationFrameId !== null) {
      cancelAnimationFrame(this.trackingAnimationFrameId);
      this.trackingAnimationFrameId = null;
    }
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach(t => t.stop());
      this.mediaStream = null;
    }
    this.isCameraActive = false;
    this.lastVideoTime = -1;
    this.lastFrameStamp = 0;
    this.liveFps = 0;
    this.lastReliableLandmarks = null;
    this.lastReliablePoseAt = 0;
    this.maskCanvas = null;
    this.maskUpdatedAt = 0;
    this.emptyPoseStreak = 0;
    if (this.cpuProbe) { this.cpuProbe.close(); this.cpuProbe = null; }
    this.clearGarmentCanvas();
    this.poseSmoother.reset();
  }

  captureSnapshot(): void {
    if (!this.videoPlayer || !this.captureCanvas) return;
    const video = this.videoPlayer.nativeElement;
    const canvas = this.captureCanvas.nativeElement;
    canvas.width = video.videoWidth || 720;
    canvas.height = video.videoHeight || 1080;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      this.uploadedPhotoUrl = canvas.toDataURL('image/jpeg', 0.92);
      this.originalPersonImageUrl = this.uploadedPhotoUrl;
      this.stopWebcam();
      this.imageSource = 'upload';
      this.runSimulation();
    }
  }

  // 3. Calibración interactiva de la prenda
  adjustScale(delta: number): void {
    this.overlayScale = Math.min(1.8, Math.max(0.5, +(this.overlayScale + delta).toFixed(2)));
  }

  adjustOffsetY(delta: number): void {
    this.overlayOffsetY = Math.min(180, Math.max(-180, this.overlayOffsetY + delta));
  }

  adjustOffsetX(delta: number): void {
    this.overlayOffsetX = Math.min(120, Math.max(-120, this.overlayOffsetX + delta));
  }

  resetOverlay(): void {
    this.overlayScale = 1.0;
    this.overlayOffsetY = 0;
    this.overlayOffsetX = 0;
    this.overlayOpacity = 0.95;
    this.blendMode = 'normal';
  }

  // 4. Inferencia con IA Generativa (IDM-VTON / Fashn.ai)
  generatePhotorealisticVTON(): void {
    if (!this.selectedProduct) return;
    const activePersonImage = this.getActivePersonImageUrl();
    if (!activePersonImage) {
      this.errorMsg = 'Debes tomarte una foto con la cámara o subir una foto para generar la prueba con IDM-VTON.';
      return;
    }

    this.isGeneratingVTON = true;
    this.errorMsg = '';
    this.successMsg = '';

    const rawGarment = (this.selectedProduct.images && this.selectedProduct.images.length > 0)
      ? this.selectedProduct.images[0].image_url
      : '';
    const garmentImg = this.resolveImg(rawGarment);

    const catName = this.isDressOrOnePiece ? 'one-pieces' : (this.isBottom ? 'bottoms' : 'tops');

    this.analiticaService.generateVTON({
      session_token: this.sessionToken,
      product_id: this.selectedProduct.id,
      variant_id: this.selectedVariant?.id,
      person_image: activePersonImage,
      garment_image: garmentImg,
      category: catName,
      model_choice: this.selectedAIModel,
      recommended_size: this.calculatedSize,
    }).subscribe({
      next: (res: VTONGenerateResult) => {
        this.vtonResult = res;
        this.isGeneratingVTON = false;
        this.activeViewMode = 'vton';
        const isPhotorealistic = res.generation_model === 'Fashn.ai' || res.generation_model.includes('Diffusion');
        const maskInfo = res.mask_confidence !== undefined
          ? ` Máscara: ${Math.round(res.mask_confidence * 100)}%${res.mask_reliable ? '' : ' (ajuste conservador)'}.`
          : '';
        this.successMsg = isPhotorealistic
          ? `Prueba fotorrealista generada para Talla ${this.calculatedSize} con ${res.generation_model} en ${res.processing_time_sec}s.${maskInfo}`
          : `Previsualización local generada para Talla ${this.calculatedSize}.${maskInfo} Configura FASHN o IDM-VTON/CatVTON para máxima fidelidad.`;
      },
      error: (err) => {
        this.isGeneratingVTON = false;
        this.errorMsg = err.error?.detail || 'Error al conectar con el motor de IA generativa VTON.';
      }
    });
  }

  getActivePersonImageUrl(): string {
    if ((this.imageSource === 'upload' || this.imageSource === 'model') && this.originalPersonImageUrl) {
      return this.originalPersonImageUrl;
    }
    return '';
  }

  // 5. Simulación biométrica y patronaje
  runSimulation(): void {
    if (!this.selectedProduct) return;
    this.loading = true;
    this.analiticaService.simulateTryon({
      session_token: this.sessionToken,
      product_id: this.selectedProduct.id,
      variant_id: this.selectedVariant?.id,
      user_height_cm: this.userHeight,
      user_weight_kg: this.userWeight,
      chest_cm: this.chestCm,
      waist_cm: this.waistCm,
      hip_cm: this.hipCm,
      photo_url: this.getActivePersonImageUrl() || undefined,
    }).subscribe({
      next: (res: VirtualTryonResult) => {
        this.simulationResult = res;
        this.garmentLandmarks = res.garment_landmarks || null;
        this.bodyLandmarks = res.body_landmarks || null;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      }
    });
  }

  // 6. Acciones comerciales y guardado
  get productPrice(): number {
    return Number(this.selectedProduct?.base_price || 0);
  }

  get reservationDeposit(): number {
    return Math.round(this.productPrice * 0.50 * 100) / 100;
  }

  get reservationBalance(): number {
    return Math.max(0, Math.round((this.productPrice - this.reservationDeposit) * 100) / 100);
  }

  getDefaultReservationDate(): string {
    const d = new Date();
    d.setDate(d.getDate() + 1);
    return d.toISOString().slice(0, 10);
  }

  get minReservationDate(): string {
    return new Date().toISOString().slice(0, 10);
  }

  buildReservedAt(): string {
    const date = this.reservationDate || this.getDefaultReservationDate();
    return `${date}T10:00:00`;
  }

  addToCart(): void {
    if (!this.selectedVariant) {
      this.errorMsg = 'Selecciona una variante antes de añadir al carrito.';
      return;
    }
    this.ventasService.addToCart(this.selectedVariant.id, 1).subscribe({
      next: () => {
        this.successMsg = `¡${this.selectedProduct?.name} (Talla ${this.simulationResult?.recommended_size || 'M'}) añadida al carrito con éxito!`;
      },
      error: (err) => {
        this.errorMsg = err.error?.detail || 'No se pudo añadir al carrito. Inicia sesión como cliente.';
      }
    });
  }

  orderOnlineDelivery(): void {
    if (!this.selectedVariant || !this.selectedProduct) {
      this.errorMsg = 'Selecciona una prenda y variante antes de pedir delivery.';
      return;
    }
    this.ventasService.addToCart(this.selectedVariant.id, 1).subscribe({
      next: () => {
        this.successMsg = `${this.selectedProduct?.name} se agrego al carrito para compra online con delivery en Santa Cruz. Completa el pago desde el carrito.`;
      },
      error: (err) => {
        this.errorMsg = err.error?.detail || 'No se pudo preparar el pedido delivery. Inicia sesion como cliente.';
      }
    });
  }

  reserveInFittingRoom(): void {
    if (!this.selectedVariant || !this.selectedProduct) return;
    this.reservasService.createReservation({
      branch_id: this.selectedBranchId,
      items: [{
        variant_id: this.selectedVariant.id,
        quantity: 1,
        notes: `Talla recomendada vestidor IA: ${this.simulationResult?.recommended_size || 'M'} | Sena 50%: Bs. ${this.reservationDeposit.toFixed(2)}`
      }],
      notes: `Reserva agendada desde Vestidor Virtual (CU32) - Sesión ${this.sessionToken}`
    }).subscribe({
      next: (res: any) => {
        this.successMsg = `¡Prenda apartada con éxito! Código: ${res.reservation_code}. Estará lista en el probador de la sucursal por 48h.`;
        setTimeout(() => {
          this.router.navigate(['/tienda/reservas']);
        }, 2200);
      },
      error: (err: any) => {
        this.errorMsg = err.error?.detail || 'Para reservar probador debes haber iniciado sesión como cliente.';
      }
    });
  }

  saveLookCapture(): void {
    if (!this.selectedProduct) return;
    const currentImg = this.vtonResult?.result_image_url || this.getActivePersonImageUrl() || (this.selectedProduct.images?.[0]?.image_url || '');
    this.analiticaService.saveCapture({
      session_token: this.sessionToken,
      product_id: this.selectedProduct.id,
      variant_id: this.selectedVariant?.id,
      photo_url: currentImg,
      generation_model: this.vtonResult ? this.vtonResult.generation_model : 'AR_HYBRID',
      recommended_size: this.simulationResult?.recommended_size || 'M',
    }).subscribe({
      next: () => {
        this.successMsg = '¡Look guardado en tu galería de capturas del vestidor virtual!';
        const link = document.createElement('a');
        link.download = `look_${this.selectedProduct?.name || 'prenda'}.jpg`;
        link.href = currentImg;
        link.click();
      },
      error: () => {
        this.errorMsg = 'Error al guardar la captura.';
      }
    });
  }

  /** Helper para acceder a propiedades de landmarks sin violar TS4111 (index signature). */
  getLandmark(key: string, fallback: number = 0): number {
    if (this.bodyLandmarks && key in this.bodyLandmarks) {
      return this.bodyLandmarks[key] as number;
    }
    return fallback;
  }
}
