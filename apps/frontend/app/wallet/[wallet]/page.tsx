"use client";

import RiskProfile from "@/components/RiskProfile";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAccount } from "wagmi";
import Moralis from "moralis";
import { Erc20Value, EvmNative } from "moralis/common-evm-utils";
import Preferences from "@/components/Preferences";
import { TokensTable } from "@/components/TokensTable";

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
  console.log(nativeBalance);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Mock token data for the table
  const mockTokens = [
    {
      id: "1",
      symbol: "USDC",
      name: "USD Coin",
      amount: "1000.00",
      value: "$1000.00",
    },
    {
      id: "2",
      symbol: "USDT",
      name: "Tether",
      amount: "500.50",
      value: "$500.50",
    },
    {
      id: "3",
      symbol: "DAI",
      name: "Dai Stablecoin",
      amount: "750.25",
      value: "$750.25",
    },
    {
      id: "4",
      symbol: "WETH",
      name: "Wrapped Ether",
      amount: "1.5",
      value: "$3000.00",
    },
    {
      id: "5",
      symbol: "WBTC",
      name: "Wrapped Bitcoin",
      amount: "0.05",
      value: "$2000.00",
    },
    {
      id: "6",
      symbol: "UNI",
      name: "Uniswap",
      amount: "100.00",
      value: "$500.00",
    },
    {
      id: "7",
      symbol: "AAVE",
      name: "Aave",
      amount: "10.00",
      value: "$800.00",
    },
    {
      id: "8",
      symbol: "LINK",
      name: "Chainlink",
      amount: "25.00",
      value: "$250.00",
    },
    {
      id: "9",
      symbol: "SNX",
      name: "Synthetix",
      amount: "200.00",
      value: "$400.00",
    },
    {
      id: "10",
      symbol: "MKR",
      name: "Maker",
      amount: "0.75",
      value: "$750.00",
    },
    {
      id: "11",
      symbol: "COMP",
      name: "Compound",
      amount: "5.00",
      value: "$300.00",
    },
    {
      id: "12",
      symbol: "YFI",
      name: "yearn.finance",
      amount: "0.01",
      value: "$250.00",
    },
  ];

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
        const tokenBalances = await Moralis.EvmApi.token.getWalletTokenBalances(
          {
            address,
            chain: "0xaa36a7", // Sepolia chain ID
          }
        );

        // Get native balance (ETH) for Sepolia
        const balance = await Moralis.EvmApi.balance.getNativeBalance({
          address,
          chain: "0xaa36a7", // Sepolia chain ID
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
  console.log("tokens", tokens);
  return (
    <>
      <Preferences address={address} />
      <div className="flex flex-col items-center justify-center">
        <div className="flex flex-col items-center justify-center">
          <h1 className="text-2xl font-bold">Wallet</h1>
          <p className="text-sm text-gray-500">{address}</p>
        </div>

        <div className="w-full max-w-4xl mt-8">
          <h1 className="text-2xl font-bold mb-4">Your Tokens</h1>
          <TokensTable data={mockTokens} />
        </div>

        <div className="w-full max-w-4xl mt-12">
          <h1 className="text-2xl font-bold mb-4">Trading Agents</h1>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                id: 1,
                name: "Alpha Seeker",
                description:
                  "Identifies alpha opportunities across DeFi protocols with emphasis on newly launched tokens.",
                image: "https://api.dicebear.com/7.x/personas/svg?seed=alpha",
              },
              {
                id: 2,
                name: "Yield Harvester",
                description:
                  "Automatically moves funds between lending protocols to maximize yield returns.",
                image: "https://api.dicebear.com/7.x/personas/svg?seed=yield",
              },
              {
                id: 3,
                name: "Arbitrage Hunter",
                description:
                  "Executes cross-DEX arbitrage opportunities for stablecoins and major pairs.",
                image:
                  "https://api.dicebear.com/7.x/personas/svg?seed=arbitrage",
              },
              {
                id: 4,
                name: "Momentum Trader",
                description:
                  "Uses technical analysis to capitalize on short-term price movements.",
                image:
                  "https://api.dicebear.com/7.x/personas/svg?seed=momentum",
              },
              {
                id: 5,
                name: "Liquidity Provider",
                description:
                  "Strategically provides liquidity to optimize fee generation across DEXes.",
                image:
                  "https://api.dicebear.com/7.x/personas/svg?seed=liquidity",
              },
              {
                id: 6,
                name: "Options Strategist",
                description:
                  "Creates and manages options strategies to hedge positions and generate income.",
                image: "https://api.dicebear.com/7.x/personas/svg?seed=options",
              },
            ].map((agent) => (
              <div
                key={agent.id}
                className="border border-gray-200 rounded-lg p-6 shadow-sm hover:shadow-md transition-shadow duration-200 flex flex-col items-center"
              >
                <div className="h-24 w-24 rounded-full overflow-hidden mb-4 bg-gray-100">
                  <img
                    src={agent.image}
                    alt={`${agent.name} profile`}
                    className="h-full w-full object-cover"
                  />
                </div>
                <h3 className="text-xl font-semibold mb-2">{agent.name}</h3>
                <p className="text-gray-600 text-center">{agent.description}</p>
                <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors">
                  Connect
                </button>
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
    </>
  );
};

export default WalletPage;
