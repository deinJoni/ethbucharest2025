"use client";

import { Button } from '@/components/ui/button';
import WalletStatistics from '@/components/WalletStatistics';
import { ArrowLeftIcon, Loader2, TrendingUpIcon } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation'
import React, { useEffect, useState } from 'react'
import { AgentOpinions } from '@/components/AgentOpinions';
import { formatEther } from 'viem';
import { useAccount } from 'wagmi';
import { Token } from '@/types';
import Moralis from 'moralis';

// Initialize Moralis outside component
if (!Moralis.Core.isStarted) {
    Moralis.start({
        apiKey: process.env.NEXT_PUBLIC_MORALIS_API_KEY,
    });
}

const TokenPage = () => {
    const { wallet, token: tokenAddress } = useParams();
    const { address } = useAccount();
    const [token, setToken] = useState<Token | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    console.log(tokenAddress);

    useEffect(() => {
        const fetchTokenData = async () => {
            if (!wallet || !tokenAddress) return;
    
            try {
                setIsLoading(true);
    
                // Special handling for native ETH
                if (tokenAddress === "0x0000000000000000000000000000000000000000") {
                    // Get native balance (ETH) for Sepolia
                    const balance = await Moralis.EvmApi.balance.getNativeBalance({
                        address: wallet as string,
                        chain: "0xaa36a7", // Sepolia chain ID
                    });
    
                    setToken({
                        id: "0x0000000000000000000000000000000000000000",
                        symbol: "ETH",
                        name: "Ethereum",
                        amount: balance.result.balance.toString(),
                        value: balance.result.balance.toString(),
                        address: "0x0000000000000000000000000000000000000000"
                    });
                }
                // Handle ERC20 tokens
                else {
                    // Get specific token data
                    const tokenData = await Moralis.EvmApi.token.getTokenMetadata({
                        addresses: [tokenAddress as string],
                        chain: "0xaa36a7", // Sepolia chain ID
                    });
    
                    // Get token balance
                    const tokenBalances = await Moralis.EvmApi.token.getWalletTokenBalances({
                        address: wallet as string,
                        chain: "0xaa36a7", // Sepolia chain ID
                        tokenAddresses: [tokenAddress as string],
                    });
    
                    if (tokenBalances.result.length > 0 && tokenData.result.length > 0) {
                        const tokenMetadata = tokenData.result[0];
                        const tokenBalance = tokenBalances.result[0];
    
                        setToken({
                            id: tokenAddress as string,
                            symbol: tokenMetadata.token.symbol || "",
                            name: tokenMetadata.token.name || "",
                            amount: tokenBalance.amount.toString(),
                            value: tokenBalance.value,
                            address: tokenAddress as string
                        });
                    } else {
                        throw new Error("Token not found");
                    }
                }
            } catch (err) {
                console.error("Error fetching token data:", err);
                setError("Failed to load token data");
            } finally {
                setIsLoading(false);
            }
        };

        fetchTokenData();
    }, [wallet, tokenAddress]);

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center h-screen">
                <Loader2 className="w-10 h-10 animate-spin" />
                Loading token data...
            </div>
        );
    }

    if (error) {
        return <div>Error: {error}</div>;
    }

    if (!token) {
        return <div>Token not found</div>;
    }

    return (
        <div className='h-full w-full'>
            <div className='flex flex-col py-4'>
                <Link
                    href={`/wallet/${wallet}`}
                    className="inline-flex items-center mb-6 text-blue-600 hover:text-blue-800"
                >
                    <svg
                        xmlns="http://www.w3.org/2000/svg"
                        className="h-5 w-5 mr-1"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                    >
                        <path
                            fillRule="evenodd"
                            d="M9.707 14.707a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 1.414L7.414 9H15a1 1 0 010 2H7.414l2.293 2.293a1 1 0 010 1.414z"
                            clipRule="evenodd"
                        />
                    </svg>
                    Back to wallet
                </Link>

                <div className='py-6'>
                    <h1 className="text-3xl font-bold mb-2">{token.name} ({token.symbol})</h1>
                    <p className="text-sm text-gray-500 break-all mb-4">
                        Contract: {token.address === "0x0000000000000000000000000000000000000000" ? "Native Token" : token.address}
                    </p>
                </div>

                <div className='py-10 flex flex-col gap-16'>
                    <WalletStatistics balance={Number(formatEther(BigInt(token.amount)))} />
                    <Button className='w-full h-[75px] bg-sky-800 text-lg font-semibold rounded-2xl hover:bg-sky-900'>
                        <TrendingUpIcon className='w-8 h-8 mr-2 animate-pulse' />
                        Analyze & Suggest
                    </Button>

                    <AgentOpinions />
                </div>
            </div>
        </div>
    )
}

export default TokenPage;