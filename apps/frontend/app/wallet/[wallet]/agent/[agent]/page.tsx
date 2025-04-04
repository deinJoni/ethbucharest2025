"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import agentsData from "@/data/agents.json";
import Link from "next/link";

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
              ? "bg-blue-600"
              : label === "Aggressiveness"
              ? "bg-red-600"
              : "bg-green-600"
          }`}
          style={{ width: `${value}%` }}
        ></div>
      </div>
    </div>
  );
};

const AgentDetailPage = () => {
  const router = useRouter();
  const params = useParams();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [loading, setLoading] = useState(true);

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
    <div className="container mx-auto px-4 py-8 max-w-4xl">
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
              src={`https://api.dicebear.com/7.x/personas/svg?seed=${agent.id}`}
              alt={`${agent.name} profile`}
              className="h-full w-full object-cover"
            />
          </div>
          <div className="mt-4 p-4 border border-gray-200 rounded-lg w-full">
            <div className="flex justify-between items-center mb-2">
              <span className="text-gray-700 font-medium">Risk Level:</span>
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
          </div>
        </div>

        <div className="md:w-2/3">
          <h1 className="text-3xl font-bold mb-2">{agent.name}</h1>
          <p className="text-xl text-gray-600 mb-6">{agent.description}</p>

          {/* Tags */}
          <div className="mb-6 flex flex-wrap gap-2">
            {agent.tags.map((tag, index) => (
              <span
                key={index}
                className="bg-gray-100 text-gray-800 px-3 py-1 rounded-full text-sm"
              >
                #{tag.replace(/\s+/g, "")}
              </span>
            ))}
          </div>

          {/* Personality */}
          <h2 className="text-2xl font-semibold mb-3">Personality</h2>
          <p className="text-gray-700 mb-6">{agent.personality}</p>

          <h2 className="text-2xl font-semibold mb-3">Strategy</h2>
          <p className="text-gray-700 mb-6">{agent.strategy}</p>

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
            </div>
          </div> */}
        </div>
      </div>
    </div>
  );
};

export default AgentDetailPage;
