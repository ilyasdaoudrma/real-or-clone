import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "GOATAT — Real or Clone | Plateforme anti-fraude vocale",
  description:
    "Détectez les voix synthétiques, le clonage vocal et les deepfakes audio grâce à l'intelligence artificielle. Authentifiez la voix, protégez la confiance.",
  keywords: ["voix synthétique", "deepfake audio", "anti-fraude", "GOATAT", "sécurité vocale"],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr" className="dark">
      <body className={`${inter.variable} font-sans antialiased bg-[#070D1A] text-slate-100`}>
        {children}
      </body>
    </html>
  );
}
