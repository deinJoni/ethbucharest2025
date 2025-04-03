"use client"

import RiskProfile from "@/components/RiskProfile";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAccount } from "wagmi";
import Moralis from "moralis";
import { Erc20Value, EvmNative } from "moralis/common-evm-utils";

// Initialize Moralis outside component
if (!Moralis.Core.isStarted) {
    Moralis.start({
        apiKey: process.env.NEXT_PUBLIC_MORALIS_API_KEY,
    });
}

const WalletPage = () => {
    const router = useRouter();
    const { address } = useAccount();

    const [tokens, setTokens] = useState<Erc20Value[]>([]);
    const [nativeBalance, setNativeBalance] = useState<EvmNative | null>(null);
    console.log(nativeBalance)
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!address) {
            router.push(`/`);
        }
    }, [address]);

    useEffect(() => {
        const fetchTokenData = async () => {
            if (!address) return;

            try {
                setIsLoading(true);

                // Get ERC20 token balances for Sepolia
                const tokenBalances = await Moralis.EvmApi.token.getWalletTokenBalances({
                    address,
                    chain: "0xaa36a7" // Sepolia chain ID
                });

                // Get native balance (ETH) for Sepolia
                const balance = await Moralis.EvmApi.balance.getNativeBalance({
                    address,
                    chain: "0xaa36a7" // Sepolia chain ID
                });

                setTokens(tokenBalances.result);
                setNativeBalance(balance.result.balance);
            } catch (err) {
                console.error("Error fetching token data:", err);
                setError("Failed to load token data");
            } finally {
                setIsLoading(false);
            }
        };

        fetchTokenData();
    }, [address]);

    if (isLoading || !address) return <div>Loading...</div>;
    if (error) return <div>Error: {error}</div>;

    return <>
        <RiskProfile address={address} />
        <div className="flex flex-col items-center justify-center">
            <div className="flex flex-col items-center justify-center">
                <h1 className="text-2xl font-bold">Wallet</h1>
                <p className="text-sm text-gray-500">{address}</p>
            </div>
            <div className="flex flex-col items-center justify-center">
                <h1 className="text-2xl font-bold">Tokens</h1>
                <div className="flex flex-col items-center justify-center">
                    {nativeBalance && tokens.length === 0 && (
                        <div>
                            <p>ETH</p>
                            <p>{Number(nativeBalance).toFixed(2)}</p>
                        </div>
                    )}
                    {tokens.map((token, index) => (
                        <div key={index} className="flex flex-col items-center justify-center">
                            <div className="grid grid-cols-2 gap-2">
                                <p>{token.token?.symbol}</p>
                                <p>{Number(token.amount).toFixed(2)}</p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    </>;
};

export default WalletPage;
