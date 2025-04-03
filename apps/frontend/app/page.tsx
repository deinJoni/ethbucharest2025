"use client";
import { useRouter } from "next/navigation";
import { useAccount } from "wagmi";
import { useEffect } from "react";
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
    <div className="h-screen grid md:grid-cols-2 min-h-full">
      {/* Left side with background image */}
      <div
        className="bg-cover bg-center w-full h-full relative"
        style={{ backgroundImage: `url('/landing-left-bg.jpg')` }}
      >
        {/* Centered label with semi-transparent background */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="bg-black/40 backdrop-blur-sm p-6 rounded-lg max-w-md text-center">
            <h1 className="text-3xl font-bold text-white mb-2">
              Web3 Portfolio Analyzer
            </h1>
            <p className="text-white/90 text-lg">
              Get insights into your crypto portfolio with advanced analytics
              and AI-powered recommendations
            </p>
          </div>
        </div>

        {/* ETH Bucharest logo in bottom left */}
        <div className="absolute bottom-8 left-8 flex flex-col items-center">
          <span className="text-md text-white font-medium drop-shadow-md">
            developed during
          </span>
          <Image
            src="/icons/eth_bucharest_logo.png"
            alt="ETH Bucharest Logo"
            width={120}
            height={120}
            className="mt-1 drop-shadow-lg"
          />
        </div>
      </div>

      {/* Right side with connect wallet */}
      <div className="h-full w-full flex items-center justify-center relative bg-gradient-to-b from-white to-gray-50 p-6">
        <div className="flex flex-col justify-center items-center text-center gap-4 max-w-md">
          <h2 className="text-2xl font-semibold text-gray-800 mb-2">
            Welcome to Your Portfolio Analyzer
          </h2>
          <p className="text-gray-600 mb-4">
            Connect your wallet to get personalized insights and analytics for
            your crypto portfolio
          </p>

          <ConnectWallet className="bg-sky-800 hover:bg-sky-900 rounded-md border-none text-white min-w-[350px] text-center py-5 font-medium transition-all shadow-md hover:shadow-lg [&>*]:text-white" />

          <span className="text-sm text-gray-500 mt-2">
            Use your own current account or set one up via Base SmartWallet
          </span>
        </div>

        {/* Icons container at the bottom */}
        <div className="absolute bottom-8 flex justify-center items-center w-full gap-6">
          {/* First group: Token metrics and Coinbase wallet */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 hover:opacity-80 transition-opacity cursor-pointer">
              <Image
                src="/icons/token_metrics.png"
                alt="Token Metrics"
                width={28}
                height={28}
              />
              <div className="flex flex-col">
                <span className="text-xs leading-tight font-medium text-black">
                  Token
                </span>
                <span className="text-xs leading-tight text-black">
                  Metrics
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2 hover:opacity-80 transition-opacity cursor-pointer">
              <Image
                src="/icons/coinbase_wallet.png"
                alt="Coinbase Wallet"
                width={28}
                height={28}
              />
              <div className="flex flex-col">
                <span className="text-xs leading-tight font-medium text-black">
                  Coinbase
                </span>
                <span className="text-xs leading-tight text-black">Wallet</span>
              </div>
            </div>
          </div>

          {/* Separator */}
          <div className="h-12 border-l border-gray-300 mx-2"></div>

          {/* Second group: FastAPI, Nest.js, and Langchain in black and white */}
          <div className="flex items-center gap-4">
            <div className="group relative">
              <Image
                src="/icons/fastapi_icon.webp"
                alt="FastAPI"
                width={32}
                height={32}
                className="filter grayscale hover:grayscale-0 transition-all duration-300"
              />
              <span className="absolute -top-8 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                FastAPI
              </span>
            </div>
            <div className="group relative">
              <Image
                src="/icons/nextjs_icon.png"
                alt="Next.js"
                width={32}
                height={32}
                className="filter grayscale hover:grayscale-0 transition-all duration-300"
              />
              <span className="absolute -top-8 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                Next.js
              </span>
            </div>
            <div className="group relative">
              <Image
                src="/icons/langchain_icon.webp"
                alt="Langchain"
                width={32}
                height={32}
                className="filter grayscale hover:grayscale-0 transition-all duration-300"
              />
              <span className="absolute -top-8 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                Langchain
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
