import React, { useEffect, useState } from 'react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './ui/card'
import { useAccount } from 'wagmi'
import { Chart } from './Chart'
import WalletBalance from './WalletBalace'
import AnalystCard from './AnalystCard'
import Link from 'next/link'
import { useParams } from 'next/navigation'
const WalletStatistics = ({ balance }: { balance: number }) => {
    const { wallet } = useParams();
    return (
        <div className='flex w-full gap-6 '>
            <div className='flex flex-col gap-2'>
                <WalletBalance balance={balance} className="" />
                {/* <Link href={`/wallet/${wallet}/analyst`}> */}
                <AnalystCard />
                {/* </Link> */}
            </div>
            <Chart className="flex-1 relative -z-[1]" />
        </div>
    )
}



export default WalletStatistics;