export function Logo({ size = 40 }: { size?: number }) {
  return (
    <div
      className="relative flex shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-aj-brand/35 to-aj-brand/10 text-aj-brand shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg viewBox="0 0 32 32" className="size-[68%]" fill="none">
        <path
          d="M16 3.5 6.5 7.2v8.1c0 6.4 4.1 10.7 9.5 13.2 5.4-2.5 9.5-6.8 9.5-13.2V7.2L16 3.5Z"
          fill="currentColor"
          fillOpacity="0.18"
          stroke="currentColor"
          strokeWidth="1.7"
        />
        <path d="M12 11.2v9.2M16 10.4v10.8M20 11.2v9.2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
        <path d="M11 14.6h10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" opacity="0.7" />
      </svg>
    </div>
  )
}
