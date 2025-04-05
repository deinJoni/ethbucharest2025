import {
  BellRing,
  Check,
  AlertCircle,
  TrendingDown,
  TrendingUp,
  PauseCircle,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function AgentOpinions({
  className,
  tokenAIInfo,
}: {
  tokenAIInfo: {
    final_summary: string;
    sma_analysis: string;
    bounce_analysis: string;
    oracle_analysis: string;
    error: string | null;
  } | null;
  className?: string;
}) {
  const getRecommendationIcon = (text: string) => {
    if (text.includes("SELL") || text.includes("sell")) {
      return <TrendingDown className="h-5 w-5 text-red-500" />;
    } else if (text.includes("BUY") || text.includes("buy")) {
      return <TrendingUp className="h-5 w-5 text-green-500" />;
    } else if (text.includes("HOLD") || text.includes("hold")) {
      return <PauseCircle className="h-5 w-5 text-yellow-500" />;
    }
    return null;
  };

  // Enhanced function to parse markdown-style formatting
  const parseMarkdown = (text: string) => {
    if (!text) return [];

    // Step 1: Split by line breaks to handle headers
    const lines = text.split("\n");

    return lines.map((line, lineIndex) => {
      // Check for headers (e.g., ### Summarize:)
      const headerMatch = line.match(/^(#{1,6})\s+(.+)$/);
      if (headerMatch) {
        const level = headerMatch[1].length; // Number of # symbols
        const headerText = headerMatch[2];

        return (
          <div key={`line-${lineIndex}`} className="mb-2">
            <h4 className={`text-${level === 3 ? "lg" : "base"} font-bold`}>
              {headerText}
            </h4>
          </div>
        );
      }

      // For non-header lines, parse bold text
      if (line.includes("**")) {
        // Split the line by ** markers
        const parts = line.split(/(\*\*[^*]+\*\*)/g);

        return (
          <div
            key={`line-${lineIndex}`}
            className={lineIndex > 0 ? "mt-2" : ""}
          >
            {parts.map((part, partIndex) => {
              // Check if this part is wrapped in ** (bold)
              if (part.startsWith("**") && part.endsWith("**")) {
                // Remove the ** markers and wrap in <strong>
                const content = part.slice(2, -2);
                return <strong key={`part-${partIndex}`}>{content}</strong>;
              }
              // Return regular text
              return <span key={`part-${partIndex}`}>{part}</span>;
            })}
          </div>
        );
      }

      // Handle empty lines as spacing
      if (line.trim() === "") {
        return <div key={`line-${lineIndex}`} className="h-2"></div>;
      }

      // Return regular text lines
      return (
        <div key={`line-${lineIndex}`} className={lineIndex > 0 ? "mt-2" : ""}>
          {line}
        </div>
      );
    });
  };

  const renderAnalysisBlock = (title: string, content: string) => {
    return (
      <div className="p-4 bg-sky-50 rounded-lg">
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-semibold text-gray-800">{title}</h3>
          <div className="flex items-center gap-1">
            {getRecommendationIcon(content)}
          </div>
        </div>
        <div className="text-sm font-medium leading-relaxed">
          {parseMarkdown(content)}
        </div>
      </div>
    );
  };

  const renderAnalysis = () => {
    if (!tokenAIInfo?.final_summary) {
      return (
        <div className="flex items-center gap-2 text-muted-foreground">
          <AlertCircle className="h-4 w-4" />
          <p className="text-sm">No analysis available</p>
        </div>
      );
    }
    return (
      <div className="flex flex-col gap-4">
        {renderAnalysisBlock("Final Summary", tokenAIInfo.final_summary)}
        {renderAnalysisBlock(
          "SMA Crossover Analysis",
          tokenAIInfo.sma_analysis
        )}
        {renderAnalysisBlock(
          "Bounce Hunter Analysis",
          tokenAIInfo.bounce_analysis
        )}
        {renderAnalysisBlock(
          "Crypto Oracle Analysis",
          tokenAIInfo.oracle_analysis
        )}
      </div>
    );
  };

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader>
        <CardTitle>Agent Opinions</CardTitle>
        <CardDescription>
          Multiple AI agents have analyzed your portfolio and provided their
          opinions.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex justify-center w-full">
        {renderAnalysis()}
      </CardContent>
      <CardFooter></CardFooter>
    </Card>
  );
}
