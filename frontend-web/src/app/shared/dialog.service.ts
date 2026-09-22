import { Injectable, NgZone } from '@angular/core';
import { BehaviorSubject, Observable } from 'rxjs';

export interface DialogConfig {
  title?: string;
  message: string;
  type?: 'warning' | 'danger' | 'info' | 'success';
  confirmText?: string;
  cancelText?: string;
  isConfirm?: boolean;
}

@Injectable({
  providedIn: 'root'
})
export class DialogService {
  private dialogState = new BehaviorSubject<{
    isOpen: boolean;
    config: DialogConfig;
    resolve?: (result: boolean) => void;
  }>({
    isOpen: false,
    config: { message: '' }
  });

  dialogState$: Observable<{
    isOpen: boolean;
    config: DialogConfig;
    resolve?: (result: boolean) => void;
  }> = this.dialogState.asObservable();

  constructor(private zone: NgZone) {
    // Interceptar window.alert nativo para que cualquier alerta del sistema
    // se dibuje con el diseño elegante de la aplicación en vez del popup del navegador
    const originalAlert = window.alert;
    window.alert = (message: any) => {
      this.zone.run(() => {
        this.alert({
          title: 'Notificación del Sistema',
          message: String(message),
          type: 'warning'
        });
      });
    };
  }

  alert(options: DialogConfig | string): Promise<void> {
    const config: DialogConfig = typeof options === 'string'
      ? { message: options, title: 'Atención', type: 'warning', confirmText: 'Entendido', isConfirm: false }
      : {
          title: options.title || 'Atención',
          message: options.message,
          type: options.type || 'warning',
          confirmText: options.confirmText || 'Entendido',
          isConfirm: false
        };

    return new Promise((resolve) => {
      this.zone.run(() => {
        this.dialogState.next({
          isOpen: true,
          config,
          resolve: () => resolve()
        });
      });
    });
  }

  confirm(options: DialogConfig | string): Promise<boolean> {
    const config: DialogConfig = typeof options === 'string'
      ? { message: options, title: 'Confirmación', type: 'warning', confirmText: 'Confirmar', cancelText: 'Cancelar', isConfirm: true }
      : {
          title: options.title || 'Confirmación',
          message: options.message,
          type: options.type || 'warning',
          confirmText: options.confirmText || 'Confirmar',
          cancelText: options.cancelText || 'Cancelar',
          isConfirm: true
        };

    return new Promise((resolve) => {
      this.zone.run(() => {
        this.dialogState.next({
          isOpen: true,
          config,
          resolve: (val: boolean) => resolve(val)
        });
      });
    });
  }

  handleAction(accepted: boolean): void {
    const current = this.dialogState.value;
    if (current.resolve) {
      current.resolve(accepted);
    }
    this.dialogState.next({
      isOpen: false,
      config: { message: '' }
    });
  }
}
