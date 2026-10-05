import type { Metadata } from "next";
import { DM_Sans, Noto_Sans_Thai } from "next/font/google";

import { AppShell } from "@/components/AppShell";

import "./globals.css";

const dmSans = DM_Sans({
  variable: "--font-dm",
  subsets: ["latin"],
});

const notoThai = Noto_Sans_Thai({
  variable: "--font-thai",
  subsets: ["thai"],
});

export const metadata: Metadata = {
  title: "E-Commerce Product Clustering",
  description: "ระบบวิเคราะห์และจัดกลุ่มสินค้าด้วย K-Means",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="th" className={`${dmSans.variable} ${notoThai.variable} h-full antialiased`}>
      <body className="min-h-full text-ink">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
