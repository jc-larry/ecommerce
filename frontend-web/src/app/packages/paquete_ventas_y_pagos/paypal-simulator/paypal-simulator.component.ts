import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { Subscription, switchMap, timer } from 'rxjs';
import {
  PayPalCaptureResult,
  PayPalCheckoutService,
  PayPalSimLoginResult
} from '../paypal-checkout.service';

type SimStep = 'CREATING' | 'EMAIL' | 'PASSWORD' | 'WALLET' | 'REVIEW' | 'PROCESSING' | 'DONE' | 'FATAL';

/**
 * [CU18 / CU26] Simulador de PayPal Checkout.
 *
 * Reproduce la ventana de PayPal (inicio de sesión en dos pasos, carga de la cartera,
 * revisión y "Completar compra") contra el backend: crea una orden simulada, el comprador
 * inicia sesión con la cuenta del simulador, aprueba y el backend captura el pago. Al
 * terminar emite `captured` con el comprobante, igual que los botones oficiales de PayPal.
 */
@Component({
  selector: 'app-paypal-simulator',
  templateUrl: './paypal-simulator.component.html',
  styleUrls: ['./paypal-simulator.component.css']
})
export class PayPalSimulatorComponent implements OnInit, OnDestroy {
  /** Monto a cobrar en bolivianos (el backend lo convierte a USD). */
  @Input() amountBob = 0;
  @Input() description = 'Compra FashionStore';
  @Input() merchantName = 'FashionStore Bolivia S.R.L.';
  @Output() captured = new EventEmitter<PayPalCaptureResult>();
  @Output() cancelled = new EventEmitter<void>();

  step: SimStep = 'CREATING';
  orderId = '';
  amountUsd = 0;

  email = '';
  password = '';
  showPassword = false;
  loginError = '';
  busy = false;

  account: PayPalSimLoginResult | null = null;
  fundingId = 'BALANCE';
  fatalError = '';
  /** Error al completar la compra: se muestra en la revisión sin cerrar la sesión. */
  reviewError = '';

  private subs = new Subscription();

  constructor(private paypal: PayPalCheckoutService) {}

  ngOnInit(): void {
    this.createOrder();
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }

  get firstName(): string {
    return this.account?.payer.name.given_name || '';
  }

  get fullName(): string {
    const n = this.account?.payer.name;
    return n ? `${n.given_name} ${n.surname}`.trim() : '';
  }

  createOrder(): void {
    this.step = 'CREATING';
    this.fatalError = '';
    this.subs.add(
      this.paypal.createSimulatedOrder(this.amountBob, this.description).subscribe({
        next: (order) => {
          this.orderId = order.id;
          this.amountUsd = order.amount_usd;
          this.step = 'EMAIL';
        },
        error: (e) => {
          this.fatalError = this.detail(e, 'No se pudo iniciar el pago con PayPal.');
          this.step = 'FATAL';
        }
      })
    );
  }

  nextFromEmail(): void {
    const email = this.email.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      this.loginError = 'Introduzca una dirección de correo electrónico válida.';
      return;
    }
    this.loginError = '';
    this.step = 'PASSWORD';
  }

  changeEmail(): void {
    this.password = '';
    this.loginError = '';
    this.step = 'EMAIL';
  }

  login(): void {
    if (!this.password || this.busy) return;
    this.busy = true;
    this.loginError = '';
    this.subs.add(
      this.paypal.simulatorLogin(this.email.trim(), this.password).subscribe({
        next: (acc) => {
          this.account = acc;
          this.busy = false;
          // Pantalla "¡Hola, …! Estamos cargando su cartera." como en PayPal.
          this.step = 'WALLET';
          this.subs.add(timer(1600).subscribe(() => (this.step = 'REVIEW')));
        },
        error: (e) => {
          this.busy = false;
          this.password = '';
          this.loginError = this.detail(e, 'No se pudo iniciar sesión. Inténtelo de nuevo.');
        }
      })
    );
  }

  /**
   * "Completar compra": el comprador aprueba y el backend captura el pago con el token de
   * aprobación. Si algo falla se queda en la revisión (con la sesión abierta) para reintentar.
   */
  completePurchase(): void {
    if (this.busy) return;
    this.busy = true;
    this.reviewError = '';
    this.step = 'PROCESSING';
    this.subs.add(
      this.paypal.simulatorApprove(this.orderId, this.email.trim(), this.password)
        .pipe(switchMap((approval) => this.paypal.captureOrder(this.orderId, approval.approval_token)))
        .subscribe({
          next: (capture) => {
            this.busy = false;
            this.step = 'DONE';
            this.subs.add(timer(1400).subscribe(() => this.captured.emit(capture)));
          },
          error: (e) => {
            this.busy = false;
            this.reviewError = this.detail(e, 'PayPal no pudo procesar el pago. No se realizó ningún cobro.');
            this.step = 'REVIEW';
          }
        })
    );
  }

  cancel(): void {
    if (this.step === 'PROCESSING' || this.step === 'DONE') return;
    this.cancelled.emit();
  }

  private detail(e: unknown, fallback: string): string {
    const d = (e as { error?: { detail?: unknown } })?.error?.detail;
    return typeof d === 'string' ? d : fallback;
  }
}
