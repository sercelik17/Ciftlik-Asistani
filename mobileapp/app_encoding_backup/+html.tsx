import { ScrollViewStyleReset } from 'expo-router/html';
import React from 'react';

// Bu dosya sadece web build'inde kullanÄ±lÄ±r.
// PWA meta etiketleri, mobil uyumluluk ve manifest linkini iÃ§erir.
export default function HTML({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr">
      <head>
        <meta charSet="utf-8" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no, viewport-fit=cover" />
        
        {/* Scroll resetleme */}
        <ScrollViewStyleReset />

        {/* PWA Manifest */}
        <link rel="manifest" href="/manifest.json" />

        {/* iOS PWA DesteÄŸi */}
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="SÃ¼t SihirbazÄ±" />
        <link rel="apple-touch-icon" href="/icon-192.png" />

        {/* Meta Renkler ve SEO */}
        <meta name="theme-color" content="#1B5E20" />
        <meta name="description" content="Yapay Zeka Destekli Ã‡iftlik YÃ¶netimi ve SÃ¼t Verim Analizi" />
      </head>
      <body>{children}</body>
    </html>
  );
}

