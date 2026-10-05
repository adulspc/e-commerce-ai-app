"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { NAV_ITEMS } from "@/lib/navigation";

const SUBTITLES: Record<string, string> = {
  "/dashboard": "See the patterns behind your products.",
  "/upload": "Bring a dataset into the workshop.",
  "/products": "Read each product against its group.",
  "/clusters": "Names describe averages, not rank.",
  "/analysis": "A suggestion, not the only answer.",
  "/processing": "From raw rows to scaled features.",
  "/export": "Take the grouped result with you.",
};

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const current = NAV_ITEMS.find((item) => item.href === pathname);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <div className="flex min-h-screen">
      {open ? (
        <button
          type="button"
          aria-label="ปิดเมนู"
          className="fixed inset-0 z-30 bg-moss/40 lg:hidden"
          onClick={() => setOpen(false)}
        />
      ) : null}
      <aside
        className={`grain fixed inset-y-0 left-0 z-40 flex w-64 shrink-0 flex-col bg-moss text-cream transition duration-200 lg:static lg:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-3 px-5 py-6">
          <LeafMark />
          <div>
            <p className="text-sm font-semibold tracking-tight">Product</p>
            <p className="text-xs text-sage">Clustering</p>
          </div>
        </div>
        <nav className="flex flex-col gap-1 px-3 pb-6" aria-label="หลัก">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition duration-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sage ${
                  active ? "bg-ivory/12 text-cream" : "text-cream/80 hover:bg-ivory/8"
                }`}
              >
                <span
                  className={`h-4 w-0.5 rounded-full ${active ? "bg-pea" : "bg-transparent"}`}
                  aria-hidden
                />
                <NavIcon href={item.href} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="min-w-0 flex-1">
        <header className="flex items-start gap-4 border-b border-line/80 px-5 py-5 sm:px-8">
          <button
            type="button"
            className="btn-secondary mt-1 lg:hidden"
            aria-label="เปิดเมนู"
            onClick={() => setOpen(true)}
          >
            เมนู
          </button>
          <div>
            <p className="text-xs tracking-[0.14em] text-pea-deep uppercase">Product Intelligence</p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
              {current?.label ?? "Product Clustering"}
            </h1>
            <p className="mt-1 text-sm text-muted">{SUBTITLES[pathname] ?? "Natural intelligence for product groups."}</p>
          </div>
        </header>
        <main className="px-5 py-6 sm:px-8 sm:py-8">{children}</main>
      </div>
    </div>
  );
}

function LeafMark() {
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden>
      <rect x="1" y="1" width="26" height="26" rx="8" stroke="#B8C39B" />
      <path d="M8 18c4-1 6-6 12-8-1 6-5 9-12 8Z" stroke="#F4F1E8" strokeWidth="1.4" />
      <path d="M9 17c2-2 4-4 7-6" stroke="#8A9A5B" strokeWidth="1.4" />
    </svg>
  );
}

function NavIcon({ href }: { href: string }) {
  const common = { width: 16, height: 16, viewBox: "0 0 16 16", fill: "none", "aria-hidden": true as const };
  if (href === "/dashboard") {
    return (
      <svg {...common}>
        <rect x="1.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" />
        <rect x="9.5" y="1.5" width="5" height="5" rx="1" stroke="currentColor" />
        <rect x="1.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" />
        <rect x="9.5" y="9.5" width="5" height="5" rx="1" stroke="currentColor" />
      </svg>
    );
  }
  if (href === "/upload") {
    return (
      <svg {...common}>
        <path d="M8 11V3M5 6l3-3 3 3" stroke="currentColor" strokeWidth="1.3" />
        <path d="M3 13h10" stroke="currentColor" strokeWidth="1.3" />
      </svg>
    );
  }
  if (href === "/products") {
    return (
      <svg {...common}>
        <path d="M2 4h12M2 8h12M2 12h8" stroke="currentColor" strokeWidth="1.3" />
      </svg>
    );
  }
  if (href === "/clusters") {
    return (
      <svg {...common}>
        <circle cx="5" cy="6" r="2" stroke="currentColor" />
        <circle cx="11" cy="6" r="2" stroke="currentColor" />
        <circle cx="8" cy="11" r="2" stroke="currentColor" />
      </svg>
    );
  }
  if (href === "/analysis") {
    return (
      <svg {...common}>
        <path d="M2 12l3-4 3 2 3-5 3 3" stroke="currentColor" strokeWidth="1.3" />
      </svg>
    );
  }
  if (href === "/processing") {
    return (
      <svg {...common}>
        <path d="M3 3h4v4H3zM9 9h4v4H9zM3 9h4" stroke="currentColor" strokeWidth="1.3" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M3 12V8M8 12V4M13 12V6" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  );
}
