'use client';

import { base } from 'wagmi/chains';
import { OnchainKitProvider as OnchainKitProviderComponent } from '@coinbase/onchainkit';
import type { ReactNode } from 'react';

export function OnchainKitProvider(props: { children: ReactNode }) {
    return (
        <OnchainKitProviderComponent
            apiKey={process.env.NEXT_PUBLIC_ONCHAINKIT_API_KEY}
            chain={base}
            config={{
                appearance: {
                    mode: 'auto',
                    theme: 'light',
                    // appearance: {
                    //   name: 'Your App Name',
                    //   logo: 'https://your-logo.com',
                    //   mode: 'auto',
                    //   theme: 'default',
                    // },
                },
                wallet: {
                    display: 'modal',
                    termsUrl: 'https://...',
                    privacyUrl: 'https://...',
                    supportedWallets: {
                        rabby: true,
                        trust: true,
                        frame: true,
                    }
                }
            }}
        >
            {props.children}
        </OnchainKitProviderComponent>
    );
}