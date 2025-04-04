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

  const renderAnalysisBlock = (title: string, content: string) => {
    return (
      <div className="p-4 bg-sky-50 rounded-lg">
        <div className="flex justify-between items-center mb-2">
          <h3 className="font-semibold text-gray-800">{title}</h3>
          <div className="flex items-center gap-1">
            {getRecommendationIcon(content)}
          </div>
        </div>
        <p className="text-sm font-medium leading-relaxed">{content}</p>
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
