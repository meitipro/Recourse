import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Recourse",
  description: "A dispute right for machine payments, adjudicated on GenLayer.",
  openGraph: {
    title: "Recourse",
    description: "A dispute right for machine payments, adjudicated on GenLayer.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="color-scheme" content="dark" />
      </head>
      <body>{children}</body>
    </html>
  );
}
