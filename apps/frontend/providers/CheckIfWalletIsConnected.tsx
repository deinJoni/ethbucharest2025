"use client";

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useAccount } from 'wagmi'
import { Loader2 } from "lucide-react"

const CheckIfWalletIsConnected = ({ children }: { children: React.ReactNode }) => {
    const { address, isConnecting } = useAccount();
    const router = useRouter();
    const [shouldRedirect, setShouldRedirect] = useState(false);

    useEffect(() => {
        // Only start the redirect timer if we're not connecting and have no address
        if (!isConnecting && !address) {
            // Set a timer to redirect after 1.5 seconds
            const timer = setTimeout(() => {
                setShouldRedirect(true);
            }, 1500);

            return () => clearTimeout(timer);
        } else {
            setShouldRedirect(false);
        }
    }, [address, isConnecting]);

    useEffect(() => {
        if (shouldRedirect) {
            router.push("/");
        }
    }, [shouldRedirect]);

    if (isConnecting) {
        return (
            <div className="flex flex-col items-center justify-center h-screen">
                <Loader2 className="w-10 h-10 animate-spin" />
                <p className="mt-2">Connecting wallet...</p>
            </div>
        );
    }

    return <>{children}</>;
}

export default CheckIfWalletIsConnected