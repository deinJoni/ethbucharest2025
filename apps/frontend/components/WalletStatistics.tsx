import React, { useEffect, useState } from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card'
import { useAccount } from 'wagmi'
import { Chart } from './Chart'
import WalletBalance from './WalletBalace'
const WalletStatistics = ({ balance }: { balance: number }) => {
    return (
        <div className='flex w-full gap-6 '>
            <div>
                <WalletBalance balance={balance} className="" />
            </div>
            <Chart className="flex-1 relative -z-[1]" />
        </div>
    )
}



export default WalletStatistics;