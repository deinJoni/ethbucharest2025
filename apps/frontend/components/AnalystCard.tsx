import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { cn } from '@/lib/utils'

const AnalystCard = ({ className }: { className?: string }) => {
    return (
        <Card className={cn("w-[350px]", className)}>
            <CardHeader>
                <CardTitle>Analyst</CardTitle>
                <CardDescription>Try out our analyst</CardDescription>
            </CardHeader>
            <CardContent>
            </CardContent>
        </Card>
    )
}

export default AnalystCard