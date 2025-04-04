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
  }, [address, router]);

  return (
    <div className="h-screen grid md:grid-cols-2 min-h-full">
      {/* Left side with background image */}
      <div
        className="w-full h-full relative landingLeft"
        style={{ backgroundImage: `url('/landing-left-bg.jpg')` }}
      >

        {/* Our logo in top left */}
        <div className="absolute top-8 left-8 flex flex-col items-left">
          <Image
            src="/icons/lmk-logo.svg"
            alt="Logo"
            width={100}
            height={75}
            className="mt-1 mb-2 drop-shadow-lg"
          />
          <span className="text-lg leading-snug text-white font-medium drop-shadow-md claimText">
            let me know <br />
            when to&nbsp;
              <span className="claimOptions relative">
                <span className="claimOption option-buy">buy</span>
                <span className="claimOption option-hold">hold</span>
                <span className="claimOption option-sell">sell</span>
              </span>
          </span>
        </div>

        {/* Centered label with semi-transparent background */}
        <div className="absolute inset-0 flex items-center justify-left left-8">
          <div className="max-w-lg text-lefts">
            <h1 className="text-5xl font-bold text-white mb-2">
              Get a portfolio managers opinion about your assets.
            </h1>
            <h2 className="text-3xl font-bold text-white mb-2">
              Based on what multiple AI agents think and your preferences.
            </h2>
          </div>
        </div>

        {/* ETH Bucharest logo in bottom left */}
        <div className="absolute bottom-8 left-8 flex flex-col items-left uppercase ">
          <span className="text-sm text-white font-medium drop-shadow-md tracking-widest">
            developed during
          </span>
          <Image
            src="/icons/eth_bucharest_logo.png"
            alt="ETH Bucharest Logo"
            width={150}
            height={55}
            className="mt-1 ethBucharestLogo drop-shadow-lg"
          />
        </div>
      </div>

      {/* Right side with connect wallet */}
      <div className="h-full w-full flex items-center justify-center relative bg-gradient-to-b from-white to-gray-50 p-6">
        <div className="flex flex-col justify-center items-center text-center gap-4 max-w-md">
          <p className="text-sky-600 font-bold mb-0">Hit the button below to get started</p>
          <ConnectWallet className="bg-sky-800 hover:bg-sky-900 rounded-md border-none  min-w-[350px] text-center text-4xl uppercase py-5 px-10 font-bold tracking-widest	 transition-all shadow-md hover:shadow-lg text-white connectButton" />
          <p className="text-sm text-gray-500 mt-1">
            Use your own current account <br />or set one up via Base SmartWallet
          </p>
        </div>

        {/* Icons container at the bottom */}
        <div className="absolute bottom-8 flex justify-center items-center w-full gap-6">
          {/* First group: Token metrics and Coinbase wallet */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 hover:opacity-80 transition-opacity cursor-pointer">
              <Image
                src="/icons/tokenmetrics-symbol.svg"
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
                src="/icons/coinbase.svg"
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
