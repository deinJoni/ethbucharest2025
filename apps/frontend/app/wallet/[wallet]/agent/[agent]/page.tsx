"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import agentsData from "@/data/agents.json";
import tokensData from "@/data/tokens.json";
import Link from "next/link";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import TokenRedirectSelect from "@/components/TokensRedirectSelect";

type Agent = {
  id: string;
  name: string;
  description: string;
  riskScore: number;
  riskLevel: string;
  strategy: string;
  indicators: string[];
  personality: string;
  tags: string[];
  stats: {
    patience: number;
    aggressiveness: number;
    adaptability: number;
  };
  strengths: string[];
  weaknesses: string[];
  improvements: string[];
  alternativeNames: string[];
  riskBreakdown: Record<string, string>;
  apiEndpoint: string;
};

type Token = {
  token_id: number;
  token_name: string;
  token_symbol: string;
};

// Add new type for analysis result
type AnalysisResult = {
  signal: string;
  llm_reasoning: string;
  error: string | null;
  steps: Array<{
    step: number;
    description: string;
    observation?: any;
    action?: string;
    action_input?: any;
    llm_output?: string;
  }>;
};

// Stat bar component to display agent stats
const StatBar = ({ label, value }: { label: string; value: number }) => {
  return (
    <div className="mb-3">
      <div className="flex justify-between mb-1">
        <span className="text-gray-700 font-medium">{label}</span>
        <span className="text-gray-600">{value}/100</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div
          className={`h-2.5 rounded-full ${
            label === "Patience"
              ? "bg-sky-600"
              : label === "Aggressiveness"
              ? "bg-rose-600"
              : "bg-teal-600"
          }`}
          style={{ width: `${value}%` }}
        ></div>
      </div>
    </div>
  );
};

// Signal result component to display trading signal
const SignalResult = ({ analysisData }: { analysisData: AnalysisResult }) => {
  const signal = analysisData.signal;
  const reasoning = analysisData.llm_reasoning;

  // Parse key metrics from the reasoning text
  const parseMetrics = (text: string) => {
    const metrics: { [key: string]: string } = {};

    // Try to extract Latest Trader Grade
    const latestTGMatch =
      text.match(
        /Latest Trader Grade \(TG\):\s*The TG for \w+ stands at (\d+\.?\d*)/i
      ) || text.match(/Latest TG:\s*(\d+\.?\d*)/i);
    if (latestTGMatch) metrics["Latest Trader Grade"] = latestTGMatch[1];

    // Try to extract 24h Trader Grade Change
    const tgcMatch =
      text.match(
        /24h Trader Grade Change \(TGC\):\s*The TGC has experienced a .* of (-?\d+\.?\d*)%/i
      ) || text.match(/TGC:\s*(-?\d+\.?\d*)%/i);
    if (tgcMatch) metrics["24h TG Change"] = tgcMatch[1] + "%";

    // Try to extract 5-Day Average TG
    const avgTGMatch =
      text.match(
        /5-Day Average TG:\s*The five-day average TG for \w+ is calculated at (\d+\.?\d*)/i
      ) || text.match(/5-Day Average TG:\s*(\d+\.?\d*)/i);
    if (avgTGMatch) metrics["5-Day Average TG"] = avgTGMatch[1];

    // Extract Quant Grade if available from API response
    if (
      analysisData.steps &&
      analysisData.steps.length > 0 &&
      analysisData.steps[0].observation &&
      analysisData.steps[0].observation.quant_grade
    ) {
      metrics["Quant Grade"] =
        analysisData.steps[0].observation.quant_grade.toFixed(2);
    }

    // Extract Momentum if available from API response
    if (
      analysisData.steps &&
      analysisData.steps.length > 0 &&
      analysisData.steps[0].observation &&
      analysisData.steps[0].observation.pct_change_tg !== undefined
    ) {
      metrics["Momentum"] =
        (analysisData.steps[0].observation.pct_change_tg * 100).toFixed(2) +
        "%";
    }

    return metrics;
  };

  // Format reasoning text for better display
  const formatReasoning = (text: string) => {
    // Check if reasoning contains a title/header
    const headerMatch = text.match(
      /\*\*([\w\s]+Trading Signal Analysis: [A-Z]+)\*\*/
    );
    const header = headerMatch ? headerMatch[1] : null;

    // If there's a header, remove it from the main text
    let mainText = text;
    if (header) {
      mainText = text.replace(
        /\*\*([\w\s]+Trading Signal Analysis: [A-Z]+)\*\*/,
        ""
      );
    }

    // Clean up markdown asterisks and format paragraphs
    mainText = mainText.replace(/\*\*/g, "").trim();

    return { header, mainText };
  };

  // Parse metrics and format reasoning
  const metrics = parseMetrics(reasoning);
  const { header, mainText } = formatReasoning(reasoning);

  // Get signal color
  const getSignalColor = (signal: string) => {
    switch (signal.toUpperCase()) {
      case "BUY":
        return "bg-green-100 text-green-800 border-green-300";
      case "SELL":
        return "bg-red-100 text-red-800 border-red-300";
      case "HOLD":
        return "bg-yellow-100 text-yellow-800 border-yellow-300";
      default:
        return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  return (
    <div className="mt-4 p-5 border rounded-md bg-white">
      <div className="flex flex-col space-y-4">
        {header && <h3 className="text-xl font-semibold">{header}</h3>}

        <div className="flex items-center">
          <div
            className={`px-4 py-2 rounded-lg text-xl font-bold ${getSignalColor(
              signal
            )}`}
          >
            {signal}
          </div>
        </div>

        {/* Display extracted metrics if available */}
        {Object.keys(metrics).length > 0 && (
          <div className="mt-2 p-4 bg-gray-50 rounded-md">
            <h3 className="text-lg font-medium mb-3">Key Metrics:</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries(metrics).map(([key, value]) => (
                <div key={key} className="flex flex-col">
                  <span className="text-sm text-gray-500">{key}</span>
                  <span className="font-semibold">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-2">
          <h3 className="text-lg font-medium mb-2">Analysis:</h3>
          <p className="text-gray-700 whitespace-pre-wrap">{mainText}</p>
        </div>
      </div>
    </div>
  );
};

// Error display component for insufficient data
const InsufficientDataError = ({
  tokenName,
  errorMessage,
}: {
  tokenName: string;
  errorMessage: string;
}) => {
  const match = errorMessage.match(/Needed (\d+) days, got (\d+)/);
  const neededDays = match ? match[1] : "sufficient";
  const gotDays = match ? match[2] : "insufficient";

  return (
    <div className="bg-orange-50 border-l-4 border-orange-500 p-4 rounded-md">
      <div className="flex items-center">
        <div className="flex-shrink-0 text-orange-500">
          <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3">
          <h3 className="text-lg font-medium text-orange-800">
            Insufficient Historical Data
          </h3>
          <div className="mt-2 text-orange-700">
            <p>
              We couldn't analyze {tokenName} due to limited historical data.
            </p>
            <p className="mt-2">
              <strong>Required:</strong> {neededDays} days of data
            </p>
            <p>
              <strong>Available:</strong> {gotDays} days of data
            </p>
          </div>
          <div className="mt-3">
            <p className="text-sm text-orange-600">
              Try again with a token that has more historical data available.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

const AgentDetailPage = () => {
  const router = useRouter();
  const params = useParams();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);
  const [openCombobox, setOpenCombobox] = useState(false);
  const [selectedTokenId, setSelectedTokenId] = useState<string>("");
  const [selectedToken, setSelectedToken] = useState<Token | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(
    null
  );
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isInsufficientData, setIsInsufficientData] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  // Filter tokens based on search query
  const filteredTokens = tokensData.filter(
    (token) =>
      token.token_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      token.token_symbol.toLowerCase().includes(searchQuery.toLowerCase())
  );

  useEffect(() => {
    if (params.agent) {
      const agentId = params.agent as string;
      const foundAgent = agentsData.agents.find((a) => a.id === agentId);

      if (foundAgent) {
        setAgent(foundAgent);
      } else {
        // Agent not found, redirect to wallet page
        router.push(`/wallet/${params.wallet}`);
      }
    }
    setLoading(false);
  }, [params.agent, params.wallet, router]);

  // Update selected token when token ID changes
  useEffect(() => {
    if (selectedTokenId) {
      const tokenIdNum = parseInt(selectedTokenId);
      const token = tokensData.find((t) => t.token_id === tokenIdNum) || null;
      setSelectedToken(token);
    } else {
      setSelectedToken(null);
    }
  }, [selectedTokenId]);

  const analyzeToken = async () => {
    if (selectedToken && agent) {
      try {
        setIsAnalyzing(true);
        setAnalysisResult(null);
        setIsInsufficientData(false);
        setErrorMessage("");

        // Prepare payload for API request
        const payload = {
          token_id: selectedToken.token_id.toString(),
          token_name: selectedToken.token_name,
        };
        console.log(process.env.NEXT_PUBLIC_API_URL);
        // Get base API URL from environment variable
        const baseApiUrl = process.env.NEXT_PUBLIC_API_URL || "";

        // Construct full URL by combining base URL with agent's endpoint
        const apiEndpoint = `${baseApiUrl}${agent.apiEndpoint}`;
        console.log(`Making API request to: ${apiEndpoint}`);

        // Make the API request
        const response = await fetch(apiEndpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        // Parse the response
        const data = await response.json();

        // Check if there's an error field in the response
        if (data.error) {
          // Extract just the main error message without all the technical details
          const errorMsg = data.error;
          const cleanedError = errorMsg.includes(":")
            ? errorMsg.split(":")[0] // Take just the first part before the colon
            : errorMsg;

          if (errorMsg.includes("Insufficient data")) {
            setIsInsufficientData(true);
            setErrorMessage(errorMsg);
          } else {
            setErrorMessage(cleanedError);
          }
        } else if (!response.ok) {
          throw new Error(`API responded with status: ${response.status}`);
        } else {
          // Handle the new response format
          setAnalysisResult(data);
        }
      } catch (error) {
        console.error("Error analyzing token:", error);
        setErrorMessage(
          error instanceof Error ? error.message : "Unknown error occurred"
        );
      } finally {
        setIsAnalyzing(false);
      }
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        Loading...
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        Agent not found
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8 w-full">
      <Link
        href={`/wallet/${params.wallet}`}
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

      <div className="flex flex-col md:flex-row items-start gap-8">
        <div className="md:w-1/3 flex flex-col items-center">
          <div className="h-48 w-48 rounded-full overflow-hidden mb-4 bg-gray-100">
            <img
              src={`/agents/${agent.id}.png`}
              alt={`${agent.name} profile`}
              className="h-full w-full object-cover"
            />
          </div>
          <div className="mt-4 p-4 border border-gray-200 rounded-lg w-full">
            <div className="flex justify-between items-center mb-2">
              <span className="text-gray-700 font-bold">Risk Level:</span>
              <span
                className={`px-2 py-1 rounded text-xs ${
                  agent.riskLevel === "Low"
                    ? "bg-green-100 text-green-800"
                    : agent.riskLevel === "Low to Moderate"
                    ? "bg-blue-100 text-blue-800"
                    : agent.riskLevel === "Moderate"
                    ? "bg-yellow-100 text-yellow-800"
                    : "bg-red-100 text-red-800"
                }`}
              >
                {agent.riskLevel} ({agent.riskScore}/10)
              </span>
            </div>

            {/* Agent Stats Bars */}
            <div className="mt-4 mb-2">
              <h3 className="text-lg font-medium mb-2">Agent Stats</h3>
              <StatBar label="Patience" value={agent.stats.patience} />
              <StatBar
                label="Aggressiveness"
                value={agent.stats.aggressiveness}
              />
              <StatBar label="Adaptability" value={agent.stats.adaptability} />
            </div>

            {/* Tags */}
            {/* <div className="mt-4">
              <h3 className="text-lg font-medium mb-2">Tags</h3>
              <div className="flex flex-wrap gap-2">
                {agent.tags.map((tag, index) => (
                  <span
                    key={index}
                    className="bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm"
                  >
                    #{tag.replace(/\s+/g, "")}
                  </span>
                ))}
              </div>
            </div> */}
          </div>
        </div>

        <div className="md:w-2/3">
          <h1 className="text-3xl font-bold mb-2">{agent.name}</h1>
          <p className="text-xl text-gray-600 mb-6">{agent.description}</p>

          {/* Token Analysis Section */}
          <div className="mb-8 p-5 border border-gray-200 rounded-lg bg-gray-50">
            <h2 className="text-2xl font-semibold mb-4">Token Analysis</h2>

            <div className="flex items-center gap-3 mb-4">
              <div className="flex-1">
                <Popover open={openCombobox} onOpenChange={setOpenCombobox}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      aria-expanded={openCombobox}
                      className="w-full justify-between h-11"
                    >
                      {selectedToken
                        ? `${selectedToken.token_name} (${selectedToken.token_symbol})`
                        : "Search for a token..."}
                      <ChevronsUpDown className="opacity-50 ml-2 h-4 w-4" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-full p-0" align="start">
                    <Command shouldFilter={false}>
                      <CommandInput
                        placeholder="Search tokens..."
                        className="h-9"
                        value={searchQuery}
                        onValueChange={setSearchQuery}
                      />
                      <CommandList>
                        <CommandEmpty>No tokens found.</CommandEmpty>
                        <CommandGroup>
                          {filteredTokens.slice(0, 50).map((token) => (
                            <CommandItem
                              key={token.token_id}
                              value={token.token_id.toString()}
                              onSelect={(value) => {
                                setSelectedTokenId(
                                  value === selectedTokenId ? "" : value
                                );
                                setOpenCombobox(false);
                              }}
                            >
                              <div className="flex flex-col">
                                <span>{token.token_name}</span>
                                <span className="text-sm text-gray-500">
                                  {token.token_symbol}
                                </span>
                              </div>
                              <Check
                                className={cn(
                                  "ml-auto",
                                  selectedTokenId === token.token_id.toString()
                                    ? "opacity-100"
                                    : "opacity-0"
                                )}
                              />
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>

              <button
                onClick={analyzeToken}
                disabled={!selectedToken || isAnalyzing}
                className={`px-4 h-11 rounded-md ${
                  selectedToken && !isAnalyzing
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "bg-gray-300 text-gray-500 cursor-not-allowed"
                } transition-colors flex items-center justify-center whitespace-nowrap`}
              >
                {isAnalyzing ? (
                  <>
                    <svg
                      className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                    Analyzing...
                  </>
                ) : (
                  "Analyze Token"
                )}
              </button>
            </div>

            {selectedToken && (
              <div className="mt-2 mb-4 p-3 bg-blue-50 rounded-md flex items-center">
                <span className="mr-2 text-blue-600">Selected:</span>
                <span className="font-medium">{selectedToken.token_name}</span>
                <span className="ml-2 px-2 py-1 bg-blue-200 text-blue-800 text-sm rounded">
                  {selectedToken.token_symbol}
                </span>
              </div>
            )}

            {isInsufficientData && (
              <InsufficientDataError
                tokenName={selectedToken?.token_name || "the token"}
                errorMessage={errorMessage}
              />
            )}

            {errorMessage && !isInsufficientData && (
              <div className="mt-4 p-4 border border-red-200 rounded-md bg-red-50">
                <div className="flex items-center text-red-800">
                  <svg
                    className="h-5 w-5 mr-2"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <h3 className="font-medium text-lg">Error</h3>
                </div>
                <p className="mt-2 ml-7 text-red-700">{errorMessage}</p>
              </div>
            )}

            {analysisResult && !isInsufficientData && !errorMessage && (
              <SignalResult analysisData={analysisResult} />
            )}
          </div>


          {/* Personality */}
          {/* <h2 className="text-2xl font-semibold mb-3">Personality</h2>
          <p className="text-gray-700 mb-6">{agent.personality}</p>

          <h2 className="text-2xl font-semibold mb-3">Strategy</h2>
          <p className="text-gray-700 mb-6">{agent.strategy}</p> */}

          {/* Strengths & Weaknesses */}
          {/* <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <h2 className="text-xl font-semibold mb-3 text-green-700">
                Strengths
              </h2>
              <ul className="list-disc pl-5 space-y-1">
                {agent.strengths.map((strength, index) => (
                  <li key={index} className="text-gray-700">
                    {strength}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h2 className="text-xl font-semibold mb-3 text-red-700">
                Weaknesses
              </h2>
              <ul className="list-disc pl-5 space-y-1">
                {agent.weaknesses.map((weakness, index) => (
                  <li key={index} className="text-gray-700">
                    {weakness}
                  </li>
                ))}
              </ul>
            </div> */}
        </div>
      </div>
    </div>
  );
};

export default AgentDetailPage;
