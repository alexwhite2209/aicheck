"use client";

import * as DialogPrimitive from "@radix-ui/react-dialog";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { X } from "lucide-react";
import * as React from "react";
import { twMerge } from "tailwind-merge";
import { clsx } from "clsx";

export const cx = (...a: Parameters<typeof clsx>) => twMerge(clsx(...a));

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-medium transition-all duration-200 disabled:pointer-events-none disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30 cursor-pointer",
  {
    variants: {
      variant: {
        primary: "bg-white text-black hover:bg-white/90 shadow-[0_0_0_1px_rgba(255,255,255,0.2),0_8px_30px_-8px_rgba(168,190,255,0.45)]",
        secondary: "bg-panel-2 text-text border border-line-2 hover:border-line-3 hover:bg-panel-3",
        ghost: "text-muted hover:text-text hover:bg-white/[0.04]",
        danger: "bg-risk/10 text-risk border border-risk/30 hover:bg-risk/15",
      },
      size: { sm: "h-8 px-3 text-[13px]", md: "h-10 px-4", lg: "h-12 px-6 text-[15px]", xl: "h-14 px-7 text-[15px] tracking-wide" },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild, ...props }, ref) => {
  const Comp = asChild ? Slot : "button";
  return <Comp ref={ref} className={cx(buttonVariants({ variant, size }), className)} {...props} />;
});
Button.displayName = "Button";

export function Badge({ children, className, color }: { children: React.ReactNode; className?: string; color?: string }) {
  return (
    <span
      className={cx("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11.5px] font-medium tracking-wide", className)}
      style={color ? { color, borderColor: `color-mix(in oklab, ${color} 35%, transparent)`, background: `color-mix(in oklab, ${color} 9%, transparent)` } : undefined}
    >
      {children}
    </span>
  );
}

export function Dot({ color, pulse }: { color: string; pulse?: boolean }) {
  return <span className={cx("inline-block size-2 rounded-full", pulse && "pulse-dot")} style={{ background: color }} />;
}

export function Label({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cx("text-[11px] font-medium uppercase tracking-[0.16em] text-dim", className)}>{children}</div>;
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={cx(
        "h-11 w-full rounded-xl border border-line-2 bg-panel px-3.5 text-[14px] text-text placeholder:text-dim outline-none transition focus:border-line-3 focus:ring-4 focus:ring-white/[0.04]",
        props.className,
      )}
    />
  );
}

export function Checkbox({ checked, onChange, children, id }: { checked: boolean; onChange: (v: boolean) => void; children: React.ReactNode; id: string }) {
  return (
    <label htmlFor={id} className="flex cursor-pointer items-start gap-3 text-[13px] leading-relaxed text-muted">
      <input id={id} type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="mt-0.5 size-4 shrink-0 accent-white" />
      <span>{children}</span>
    </label>
  );
}

export const Dialog = DialogPrimitive.Root;
export const DialogTrigger = DialogPrimitive.Trigger;
export const DialogClose = DialogPrimitive.Close;

export function DialogContent({ children, title, className, wide }: { children: React.ReactNode; title: string; className?: string; wide?: boolean }) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm data-[state=open]:animate-in" />
      <DialogPrimitive.Content
        className={cx(
          "panel fixed left-1/2 top-1/2 z-50 max-h-[86vh] w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-2xl p-6 shadow-2xl focus:outline-none",
          wide ? "max-w-3xl" : "max-w-xl",
          className,
        )}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <DialogPrimitive.Title className="text-[17px] font-semibold tracking-tight">{title}</DialogPrimitive.Title>
          <DialogPrimitive.Close className="rounded-lg p-1 text-dim hover:bg-white/5 hover:text-text" aria-label="Закрыть">
            <X className="size-4" />
          </DialogPrimitive.Close>
        </div>
        <DialogPrimitive.Description className="sr-only">{title}</DialogPrimitive.Description>
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  );
}

export function Tip({ children, content }: { children: React.ReactNode; content: React.ReactNode }) {
  return (
    <TooltipPrimitive.Provider delayDuration={150}>
      <TooltipPrimitive.Root>
        <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
        <TooltipPrimitive.Portal>
          <TooltipPrimitive.Content sideOffset={6} className="z-50 max-w-xs rounded-lg border border-line-2 bg-panel-3 px-3 py-2 text-[12px] leading-relaxed text-muted shadow-xl">
            {content}
          </TooltipPrimitive.Content>
        </TooltipPrimitive.Portal>
      </TooltipPrimitive.Root>
    </TooltipPrimitive.Provider>
  );
}
