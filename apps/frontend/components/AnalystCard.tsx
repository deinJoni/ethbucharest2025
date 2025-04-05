import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { cn } from '@/lib/utils'
import { Button } from './ui/button'

const AnalystCard = ({ className }: { className?: string }) => {
    return (
        <Card className={cn("w-[350px]", className)}>
            <CardHeader>
                <CardTitle>Analyst</CardTitle>
                <CardDescription></CardDescription>
            </CardHeader>
            <CardContent>
                <Button disabled variant="outline" className="analyzeWholePortfolioButton">Analyze whole portfolio (coming soon)</Button>
            </CardContent>
        </Card>
    )
}

export default AnalystCard