import './globals.css';
import { Suspense } from 'react';
import { Cormorant_Garamond, Noto_Sans_KR, Noto_Serif_KR } from 'next/font/google';
import { FeedbackProvider } from '@/components/feedback/FeedbackProvider';

const notoSansKr = Noto_Sans_KR({
  weight: ['400', '500', '700'],
  variable: '--font-noto-sans-kr',
  display: 'swap',
  preload: false,
});

const notoSerifKr = Noto_Serif_KR({
  weight: ['600', '700'],
  variable: '--font-noto-serif-kr',
  display: 'swap',
  preload: false,
});

const cormorantGaramond = Cormorant_Garamond({
  subsets: ['latin'],
  weight: ['600', '700'],
  variable: '--font-cormorant-garamond',
  display: 'swap',
});

export const metadata = {
  title: 'Joolife Dashboard',
  description: 'Premium Hanwoo Farm Management System',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'Joolife',
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className={`${notoSansKr.variable} ${notoSerifKr.variable} ${cormorantGaramond.variable}`}>
        <FeedbackProvider><Suspense>{children}</Suspense></FeedbackProvider>
      </body>
    </html>
  );
}
