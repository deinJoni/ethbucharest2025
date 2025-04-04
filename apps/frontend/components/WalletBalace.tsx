import { cn } from "@/lib/utils";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card"

const WalletBalance = ({ balance, className }: { balance: number, className?: string }) => {
    return (
        <Card className={cn("w-[350px]", className)}>   
            <CardHeader>
                <CardTitle>Total Balance</CardTitle>
                <CardDescription>The total balance of your wallet.</CardDescription>
            </CardHeader>
            <CardContent>
                <div className="flex items-center justify-between">
                    <p className="text-3xl font-bold">ETH {balance.toFixed(4)}</p>
                </div>
            </CardContent>
        </Card>
    )
}

export default WalletBalance;