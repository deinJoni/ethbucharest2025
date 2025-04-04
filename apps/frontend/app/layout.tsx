import '@coinbase/onchainkit/styles.css';
import type { Metadata } from 'next';
import './globals.css';
import { OnchainKitProvider } from '@/providers/OnchainKitProvider';
import { ThemeProvider } from '@/providers/ThemeProvider';
import { Toaster } from '@/components/ui/toaster';
import CheckIfWalletIsConnected from '@/providers/CheckIfWalletIsConnected';

export const metadata: Metadata = {
  title: "Let Me Know",
  description: 'Let Me Know',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="bg-background">
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          disableTransitionOnChange
        >
          <div className="w-full h-full">
            <OnchainKitProvider>
              <CheckIfWalletIsConnected>
                {/* <Navbar /> */}
                {children}
              </CheckIfWalletIsConnected>
            </OnchainKitProvider>
            <Toaster />
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
