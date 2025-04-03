"use client";
import { useRouter } from "next/navigation";
import { useAccount } from "wagmi";
import { useEffect } from "react";
import { Avatar, Name } from "@coinbase/onchainkit/identity";
import { ConnectWallet } from "@coinbase/onchainkit/wallet";
import Image from "next/image";

export default function App() {
  const router = useRouter();
  const { address } = useAccount();

  useEffect(() => {
    if (address) {
      router.push(`/wallet/${address}`);
    }
  }, [address]);

  return (
    <div className="h-screen grid grid-cols-2 min-h-full">
      <div
        className="bg-cover bg-center w-full h-full relative"
        style={{ backgroundImage: `url('/landing-left-bg.jpg')` }}
      >
        {/* ETH Bucharest logo in bottom left */}
        <div className="absolute bottom-8 left-8 flex flex-col items-center">
          <span className="text-md text-white font-medium">
            developed during
          </span>
          <Image
            src="/icons/eth_bucharest_logo.png"
            alt="ETH Bucharest Logo"
            width={120}
            height={120}
            className="mt-1"
          />
        </div>
      </div>
      <div className="h-full w-full flex items-center justify-center relative">
        <div className="flex flex-col justify-center items-center text-center gap-2">
          <span className="">Hit the button below to get started</span>
          <ConnectWallet className="bg-sky-900 hover:bg-sky-800 rounded-sm border-[1px] border-sky-900 text-red-500 min-w-[350px] text-center py-5"></ConnectWallet>
          <span className="text-sm">
            Use your wn current account or set one up via Base SmartWallet
          </span>
        </div>

        {/* Icons container at the bottom */}
        <div className="absolute bottom-8 flex justify-center items-center w-full gap-6">
          {/* First group: Token metrics and Coinbase wallet */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Image
                src="/icons/token_metrics.png"
                alt="Token Metrics"
                width={28}
                height={28}
              />
              <div className="flex flex-col">
                <span className="text-xs leading-tight">Token</span>
                <span className="text-xs leading-tight">Metrics</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Image
                src="/icons/coinbase_wallet.png"
                alt="Coinbase Wallet"
                width={28}
                height={28}
              />
              <div className="flex flex-col">
                <span className="text-xs leading-tight">Coinbase</span>
                <span className="text-xs leading-tight">Wallet</span>
              </div>
            </div>
          </div>

          {/* Separator */}
          <div className="h-12 border-l border-gray-300 mx-2"></div>

          {/* Second group: FastAPI, Nest.js, and Langchain in black and white */}
          <div className="flex items-center gap-4">
            <Image
              src="/icons/fastapi_icon.webp"
              alt="FastAPI"
              width={32}
              height={32}
              className="filter grayscale"
            />
            <Image
              src="/icons/nextjs_icon.png"
              alt="Next.js"
              width={32}
              height={32}
              className="filter grayscale"
            />
            <Image
              src="/icons/langchain_icon.webp"
              alt="Langchain"
              width={32}
              height={32}
              className="filter grayscale"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
