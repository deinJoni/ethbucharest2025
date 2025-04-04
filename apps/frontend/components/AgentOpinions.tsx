import { BellRing, Check } from "lucide-react"

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

type Opinion = {
    agent: string;
    title: string;
    description: string;
    sentiment: 'positive' | 'neutral' | 'negative';
    confidence: number;
}

const opinions: Opinion[] = [
    {
        agent: "Risk Analyzer",
        title: "Market volatility suggests caution",
        description: "Current market conditions show increased volatility. Consider reducing position size.",
        sentiment: 'neutral',
        confidence: 0.75
    },
    {
        agent: "Trend Analyst",
        title: "Bullish momentum detected",
        description: "Technical indicators suggest upward trend continuation over next 2-3 weeks.",
        sentiment: 'positive',
        confidence: 0.82
    },
    {
        agent: "Value Assessor",
        title: "Token appears overvalued",
        description: "Current price exceeds fundamental value metrics by 15%. Consider taking profits.",
        sentiment: 'negative',
        confidence: 0.68
    }
]


type CardProps = React.ComponentProps<typeof Card>

export function AgentOpinions({ className, ...props }: CardProps) {
    return (
        <Card className={cn("w-full", className)} {...props}>
            <CardHeader>
                <CardTitle>Agent Opinions</CardTitle>
                <CardDescription>Multiple AI agents have analyzed your portfolio and provided their opinions.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4">
                <div>
                    {opinions.map((opinion, index) => (
                        <div
                            key={index}
                            className="mb-4 grid grid-cols-[25px_1fr] items-start pb-4 last:mb-0 last:pb-0"
                        >
                            <span className="flex h-2 w-2 translate-y-1 rounded-full bg-sky-500" />
                            <div className="space-y-1">
                                <p className="text-sm font-medium leading-none">
                                    {opinion.title}
                                </p>
                                <p className="text-sm text-muted-foreground">
                                    {opinion.description}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            </CardContent>
            <CardFooter>

            </CardFooter>
        </Card>
    )
}
