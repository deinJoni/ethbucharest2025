import { BellRing, Check, AlertCircle } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"

export function AgentOpinions({ className, tokenAIInfo }: {
    tokenAIInfo: {
        final_summary: string;
        sma_analysis: string;
        bounce_analysis: string;
        oracle_analysis: string;
        error: string | null;
    } | null,
    className?: string;
}) {
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
                <div className="p-4 bg-sky-50 rounded-lg">
                    <p className="text-sm font-medium leading-relaxed">{tokenAIInfo.final_summary}</p>
                </div>
                <div className="p-4 bg-sky-50 rounded-lg">
                    <p className="text-sm font-medium leading-relaxed">{tokenAIInfo.sma_analysis}</p>
                </div>
                <div className="p-4 bg-sky-50 rounded-lg">
                    <p className="text-sm font-medium leading-relaxed">{tokenAIInfo.bounce_analysis}</p>
                </div>
                <div className="p-4 bg-sky-50 rounded-lg">
                    <p className="text-sm font-medium leading-relaxed">{tokenAIInfo.oracle_analysis}</p>
                </div>
            </div>
        );
    };

    return (
        <Card className={cn("w-full", className)}>
            <CardHeader>
                <CardTitle>Agent Opinions</CardTitle>
                <CardDescription>
                    Multiple AI agents have analyzed your portfolio and provided their opinions.
                </CardDescription>
            </CardHeader>
            <CardContent className="flex justify-center w-full">
                {renderAnalysis()}
            </CardContent>
            <CardFooter>

            </CardFooter>
        </Card>
    )
}
