"use client"

import Preferences from "@/components/Preferences";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAccount } from "wagmi";


const WalletPage = () => {
    const router = useRouter();
    const { address } = useAccount();

    useEffect(() => {
        if (!address) {
            router.push(`/`);
        }
    }, [address]);

    if (!address) {
        return <div>Loading...</div>;
    }

    return <>
        <Preferences address={address} />
    </>;
};

export default WalletPage;
