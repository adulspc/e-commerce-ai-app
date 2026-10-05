"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV_ITEMS } from "@/lib/navigation";

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-line bg-ivory">
      <div className="border-b border-line px-5 py-5">
        <p className="text-sm font-semibold tracking-tight">Product Clustering</p>
        <p className="mt-1 text-xs text-muted">K-Means</p>
      </div>
      <nav className="flex flex-col gap-1 p-3">
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={
                active
                  ? "rounded-md bg-pea-deep px-3 py-2 text-sm text-white"
                  : "rounded-md px-3 py-2 text-sm text-ink hover:bg-foam"
              }
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
