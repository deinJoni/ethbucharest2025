// 'use client';

// import { base } from 'wagmi/chains';
// import { OnchainKitProvider } from '@coinbase/onchainkit';
// import type { ReactNode } from 'react';
// import { ThemeProvider as NextThemesProvider } from "next-themes"

// export function Providers(props: { children: ReactNode }) {
//   return (
//     <NextThemesProvider
//       attribute="class"
//       defaultTheme="light"
//       enableSystem
//       disableTransitionOnChange
//     >
//       <OnchainKitProvider
//         apiKey={process.env.NEXT_PUBLIC_ONCHAINKIT_API_KEY}
//         chain={base}
//         config={{
//           appearance: {
//             mode: 'auto',
//             // appearance: {
//             //   name: 'Your App Name',
//             //   logo: 'https://your-logo.com',
//             //   mode: 'auto',
//             //   theme: 'default',
//             // },
//           },
//           wallet: {
//             display: 'modal',
//             termsUrl: 'https://...',
//             privacyUrl: 'https://...',
//             supportedWallets: {
//               rabby: true,
//               trust: true,
//               frame: true,
//             }
//           }
//         }}
//       >
//         {props.children}
//       </OnchainKitProvider>
//     </NextThemesProvider>
//   );
// }