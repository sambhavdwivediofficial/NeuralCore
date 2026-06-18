import '@testing-library/jest-dom';

// recharts calls ResizeObserver internally, which doesn't exist in jsdom.
// A minimal stub is enough since we don't test actual resize behavior.
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Radix UI's Select/Popover components rely on pointer capture APIs that
// jsdom doesn't implement, which otherwise makes userEvent.click() fail
// with a "pointer-events: none" error on the open dropdown.
if (typeof window !== 'undefined') {
  window.HTMLElement.prototype.hasPointerCapture = window.HTMLElement.prototype.hasPointerCapture || (() => false);
  window.HTMLElement.prototype.setPointerCapture = window.HTMLElement.prototype.setPointerCapture || (() => {});
  window.HTMLElement.prototype.releasePointerCapture = window.HTMLElement.prototype.releasePointerCapture || (() => {});
  window.HTMLElement.prototype.scrollIntoView = window.HTMLElement.prototype.scrollIntoView || (() => {});

  // jsdom has no PointerEvent constructor at all, which Radix UI's Select
  // depends on to detect real pointer interactions. Without it, Radix
  // falls back to a guarded state that renders the trigger as effectively
  // disabled (pointer-events: none) in tests.
  if (typeof window.PointerEvent === 'undefined') {
    class PointerEvent extends MouseEvent {
      constructor(type, props = {}) {
        super(type, props);
        this.pointerId = props.pointerId ?? 1;
        this.width = props.width ?? 1;
        this.height = props.height ?? 1;
        this.pressure = props.pressure ?? 0;
        this.tangentialPressure = props.tangentialPressure ?? 0;
        this.tiltX = props.tiltX ?? 0;
        this.tiltY = props.tiltY ?? 0;
        this.twist = props.twist ?? 0;
        this.pointerType = props.pointerType ?? 'mouse';
        this.isPrimary = props.isPrimary ?? true;
      }
    }
    window.PointerEvent = PointerEvent;
  }
}
