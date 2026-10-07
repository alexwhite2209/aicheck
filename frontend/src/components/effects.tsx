"use client";

import { motion, useInView, useMotionValue, useReducedMotion, useScroll, useSpring, useTransform } from "framer-motion";
import * as React from "react";
import { cx } from "./ui";

/* Световое пятно, следующее за курсором внутри контейнера */
export function Spotlight({ className, size = 520 }: { className?: string; size?: number }) {
  const ref = React.useRef<HTMLDivElement>(null);
  const x = useMotionValue(-1000);
  const y = useMotionValue(-1000);
  const sx = useSpring(x, { stiffness: 120, damping: 20, mass: 0.6 });
  const sy = useSpring(y, { stiffness: 120, damping: 20, mass: 0.6 });
  React.useEffect(() => {
    const el = ref.current?.parentElement;
    if (!el) return;
    const move = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      x.set(e.clientX - r.left);
      y.set(e.clientY - r.top);
    };
    el.addEventListener("pointermove", move);
    return () => el.removeEventListener("pointermove", move);
  }, [x, y]);
  const bg = useTransform([sx, sy], ([a, b]) => `radial-gradient(${size}px circle at ${a}px ${b}px, rgba(168,190,255,0.10), transparent 60%)`);
  return <motion.div ref={ref} aria-hidden className={cx("pointer-events-none absolute inset-0", className)} style={{ background: bg }} />;
}

/* Магнитная кнопка: слегка тянется к курсору */
export function Magnetic({ children, strength = 0.25 }: { children: React.ReactNode; strength?: number }) {
  const ref = React.useRef<HTMLDivElement>(null);
  const x = useSpring(0, { stiffness: 250, damping: 18 });
  const y = useSpring(0, { stiffness: 250, damping: 18 });
  const reduce = useReducedMotion();
  return (
    <motion.div
      ref={ref}
      style={{ x, y }}
      className="inline-block"
      onPointerMove={(e) => {
        if (reduce || !ref.current) return;
        const r = ref.current.getBoundingClientRect();
        x.set((e.clientX - (r.left + r.width / 2)) * strength);
        y.set((e.clientY - (r.top + r.height / 2)) * strength);
      }}
      onPointerLeave={() => {
        x.set(0);
        y.set(0);
      }}
    >
      {children}
    </motion.div>
  );
}

/* Слова выплывают из-под линии (без побуквенных эффектов) */
export function RiseWords({ text, className, delay = 0, as: Tag = "span" }: { text: string; className?: string; delay?: number; as?: "span" | "h1" | "h2" | "p" }) {
  const words = text.split(" ");
  const MotionTag = motion[Tag];
  return (
    <MotionTag className={className} initial="hidden" whileInView="show" viewport={{ once: true, margin: "-40px" }} aria-label={text}>
      {words.map((w, i) => (
        <span key={i} className="inline-block overflow-hidden pb-[0.12em] align-bottom" aria-hidden>
          <motion.span
            className="inline-block"
            variants={{ hidden: { y: "110%" }, show: { y: "0%" } }}
            transition={{ duration: 0.75, ease: [0.22, 1, 0.36, 1], delay: delay + i * 0.045 }}
          >
            {w}
            {i < words.length - 1 ? " " : ""}
          </motion.span>
        </span>
      ))}
    </MotionTag>
  );
}

/* Карточка с наклоном за курсором и бликом */
export function TiltCard({ children, className, max = 7 }: { children: React.ReactNode; className?: string; max?: number }) {
  const ref = React.useRef<HTMLDivElement>(null);
  const rx = useSpring(0, { stiffness: 180, damping: 18 });
  const ry = useSpring(0, { stiffness: 180, damping: 18 });
  const gx = useMotionValue(50);
  const gy = useMotionValue(50);
  const glare = useTransform([gx, gy], ([a, b]) => `radial-gradient(420px circle at ${a}% ${b}%, rgba(255,255,255,0.07), transparent 55%)`);
  const reduce = useReducedMotion();
  return (
    <motion.div
      ref={ref}
      className={cx("relative [transform-style:preserve-3d]", className)}
      style={{ rotateX: rx, rotateY: ry, transformPerspective: 1100 }}
      onPointerMove={(e) => {
        if (reduce || !ref.current) return;
        const r = ref.current.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width;
        const py = (e.clientY - r.top) / r.height;
        ry.set((px - 0.5) * max * 2);
        rx.set(-(py - 0.5) * max * 2);
        gx.set(px * 100);
        gy.set(py * 100);
      }}
      onPointerLeave={() => {
        rx.set(0);
        ry.set(0);
      }}
    >
      {children}
      <motion.div aria-hidden className="pointer-events-none absolute inset-0 rounded-[inherit]" style={{ background: glare }} />
    </motion.div>
  );
}

/* Выезд блока при прокрутке с параллаксом; направление задаётся для группы */
export function SlideIn({ children, from = "bottom", className, delay = 0, parallax = 0 }: {
  children: React.ReactNode; from?: "left" | "right" | "bottom"; className?: string; delay?: number; parallax?: number;
}) {
  const ref = React.useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: "-80px" });
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start end", "end start"] });
  const py = useTransform(scrollYProgress, [0, 1], [parallax, -parallax]);
  const off = from === "left" ? { x: -70 } : from === "right" ? { x: 70 } : { y: 50 };
  return (
    <motion.div ref={ref} style={parallax ? { y: py } : undefined} className={className}>
      <motion.div
        initial={{ opacity: 0, ...off }}
        animate={inView ? { opacity: 1, x: 0, y: 0 } : undefined}
        transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1], delay }}
        className="h-full"
      >
        {children}
      </motion.div>
    </motion.div>
  );
}

/* Плавный счётчик числа */
export function CountUp({ value, duration = 1.2, format }: { value: number; duration?: number; format?: (v: number) => string }) {
  const [v, setV] = React.useState(0);
  React.useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / (duration * 1000));
      const eased = 1 - Math.pow(1 - p, 3);
      setV(value * eased);
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  return <>{format ? format(v) : Math.round(v)}</>;
}
