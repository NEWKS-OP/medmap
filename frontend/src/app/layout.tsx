import type { Metadata } from "next";
import "./globals.css";
import { MobileNav, Nav } from "@/components/nav";

export const metadata: Metadata = {
  title: "MEDMAP — Smart Health Data Mapping",
  description: "Harmonize heterogeneous clinical data sources into one model, with quality, lineage and corrections.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen">
        <div className="flex">
          <Nav />
          <div className="min-w-0 flex-1">
            <MobileNav />
            <main className="mx-auto max-w-7xl p-4 md:p-6">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
