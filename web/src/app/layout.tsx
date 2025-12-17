import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CAPE Agent",
  description: "AI 能力助手",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
