"use client";

import RiskProfile from "@/components/RiskProfile";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAccount } from "wagmi";
import Moralis from "moralis";
import { Erc20Value, EvmNative } from "moralis/common-evm-utils";
import Preferences from "@/components/Preferences";
import { TokensTable } from "@/components/TokensTable";
import { Token } from "@/types";
import WalletStatistics from "@/components/WalletStatistics";
import { formatEther } from "@/lib/utils";
import { Loader2 } from "lucide-react";
import agentsData from "@/data/agents.json";
import Link from "next/link";
import TokenRedirectSelect from "@/components/TokensRedirectSelect";
// Initialize Moralis outside component
if (!Moralis.Core.isStarted) {
  Moralis.start({
    apiKey: process.env.NEXT_PUBLIC_MORALIS_API_KEY,
  });
}

const WalletPage = () => {
  const router = useRouter();
  const { address } = useAccount();

  const [tokens, setTokens] = useState<Token[]>([]);
  // const [nativeBalance, setNativeBalance] = useState<EvmNative | null>(null);
  const [nativeBalance, setNativeBalance] = useState<Token | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTokenData = async () => {
      if (!address) return;

      try {
        setIsLoading(true);

        // Get ERC20 token balances for Sepolia
        const tokenBalances = await Moralis.EvmApi.token.getWalletTokenBalances({
          address,
          chain: "0xaa36a7", // Sepolia chain ID
        });

        // Get native balance (ETH) for Sepolia
        const balance = await Moralis.EvmApi.balance.getNativeBalance({
          address,
          chain: "0xaa36a7", // Sepolia chain ID
        });

        // Create native token object
        const nativeToken = {
          id: "0x0000000000000000000000000000000000000000", // Standard address for native ETH
          symbol: "ETH",
          name: "Ethereum",
          amount: balance.result.balance.toString(),
          value: balance.result.balance.toString(),
          address: "0x0000000000000000000000000000000000000000",
        };

        // Set native balance separately (if you still need this for other components)
        setNativeBalance(nativeToken);

        // Map ERC20 tokens
        const erc20Tokens = tokenBalances.result.map((token, index) => ({
          id: token.token?.contractAddress?.toString() || "",
          symbol: token.token?.symbol ?? "",
          name: token.token?.name ?? "",
          amount: token.amount.toString(),
          value: token.value,
          address: token.token?.contractAddress?.toString() ?? "",
        }));

        // Combine native token with ERC20 tokens
        setTokens([nativeToken, ...erc20Tokens]);

      } catch (err) {
        console.error("Error fetching token data:", err);
        setError("Failed to load token data");
      } finally {
        setIsLoading(false);
      }
    };

    fetchTokenData();
  }, [address]);

  if (isLoading || !address)
    return (
      <div className="flex flex-col items-center justify-center h-screen">
        <Loader2 className="w-10 h-10 animate-spin" />
        Loading...
      </div>
    );
  if (error) return <div>Error: {error}</div>;
  return (
    <div className="w-full flex justify-center">
      <Preferences address={address} />
      <div className="flex flex-col items-center justify-center py-10">
        {/* <div className="flex flex-col items-center justify-center mt-5">
          <h1 className="text-2xl font-bold">Wallet</h1>
          <p className="text-sm text-gray-500">{address}</p>
        </div> */}

        <WalletStatistics balance={formatEther(nativeBalance?.amount ?? 0)} />

        <div className="w-full mt-16">
          <h1 className="text-2xl font-bold mb-4">Your Tokens</h1>
          <TokensTable data={[...tokens]} />
        </div>

        <div className="w-full py-10">
          <h1 className="text-2xl font-bold mb-4">Search for a token and get AI analysis</h1>
          <TokenRedirectSelect />
        </div>


        <div className="w-full mt-12">
          <h1 className="text-2xl font-bold mb-4">Trading Agents</h1>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {agentsData.agents.map((agent) => (
              <div
                key={agent.id}
                className="border border-gray-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow duration-200 flex flex-col items-center"
              >
                <div className="h-24 w-24 rounded-full overflow-hidden mb-4 bg-gray-100">
                  <img
                    src={`/agents/${agent.id}.png`}
                    alt={`${agent.name} profile`}
                    className="h-full w-full object-cover"
                  />
                </div>
                <h3 className="text-xl font-semibold mb-2">{agent.name}</h3>
                <p className="text-gray-700 font-light text-xs mb-0">
                  Risk Level
                </p>
                <div className="flex items-center mt-0 mb-3">
                  <span
                    className={`px-2 py-1 rounded text-xs font-bold ${agent.riskLevel === "Low"
                      ? "bg-green-100 text-green-800"
                      : agent.riskLevel === "Low to Moderate"
                        ? "bg-blue-100 text-blue-800"
                        : agent.riskLevel === "Moderate"
                          ? "bg-yellow-100 text-yellow-800"
                          : "bg-red-100 text-red-800"
                      }`}
                  >
                    {agent.riskLevel}
                  </span>
                </div>

                <p className="text-gray-600 text-center">{agent.shortdesc}</p>
                <Link href={`/wallet/${address}/agent/${agent.id}`}>
                  <button className="mt-4 px-4 py-2 bg-sky-800 text-white rounded-md hover:bg-blue-700 transition-colors">
                    View Details
                  </button>
                </Link>
              </div>
            ))}
          </div>
        </div>

        {/* <div className="flex flex-col items-center justify-center mt-8">
          <h1 className="text-2xl font-bold">Original Tokens Display</h1>
          <div className="flex flex-col items-center justify-center">
            {nativeBalance && tokens.length === 0 && (
              <div>
                <p>ETH</p>
                <p>{Number(nativeBalance).toFixed(2)}</p>
              </div>
            )}
            {tokens.map((token, index) => (
              <div
                key={index}
                className="flex flex-col items-center justify-center"
              >
                <div className="grid grid-cols-2 gap-2">
                  <p>{token.token?.symbol}</p>
                  <p>{Number(token.amount).toFixed(2)}</p>
                </div>
              </div>
            ))}
          </div>
        </div> */}
      </div>
    </div>
  );
};

export default WalletPage;
