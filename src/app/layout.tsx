import type { Metadata } from "next";
import { Heebo, Assistant } from "next/font/google";
import "./globals.css";

const heebo = Heebo({ subsets: ["hebrew"], variable: "--font-heebo" });
const assistant = Assistant({ subsets: ["hebrew"], variable: "--font-assistant" });

export const metadata: Metadata = {
  title: "מחולל תיאורי בשמים | AI Perfume Generator",
  description: "צור תיאורים מקצועיים ויצירתיים לבשמים באמצעות בינה מלאכותית",
  openGraph: {
    title: "מחולל תיאורי בשמים | AI Perfume Generator",
    description: "צור תיאורים מקצועיים ויצירתיים לבשמים באמצעות בינה מלאכותית",
    type: "website",
    locale: "he_IL",
  }
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  // AEO JSON-LD Schema
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "name": "מחולל תיאורי בשמים",
    "description": "צור תיאורים מקצועיים ויצירתיים לבשמים באמצעות בינה מלאכותית",
    "applicationCategory": "UtilityApplication",
    "operatingSystem": "Any",
    "offers": {
      "@type": "Offer",
      "price": "0"
    }
  };

  return (
    <html lang="he" dir="rtl" className="dark">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className={`${assistant.className} ${heebo.variable} antialiased dark`}>
        {children}
      </body>
    </html>
  );
}
