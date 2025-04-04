"use client";

import { Button } from '@/components/ui/button';
import WalletStatistics from '@/components/WalletStatistics';
import { ArrowLeftIcon, TrendingUpIcon } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation'
import React from 'react'
import { AgentOpinions } from '@/components/AgentOpinions';
const TokenPage = () => {
    // const { wallet, token } = useParams();
    const params = useParams();
    return (
        <div className='h-full w-full'>
            <div className='flex flex-col py-4'>
                {/* <Button asChild variant="outline"> */}
                {/* <ArrowLeftIcon className='w-4 h-4' /> */}
                {/* <Link href={`/wallet/${wallet}`}>Back</Link> */}
                {/* </Button> */}
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

                <div className='py-10 flex flex-col gap-16'>
                    <WalletStatistics balance={100} />
                    <Button className='w-full h-[75px] bg-sky-800 text-lg font-semibold rounded-2xl hover:bg-sky-900'>
                        <TrendingUpIcon className='w-8 h-8 mr-2 animate-pulse' />
                        Analyze & Suggest
                    </Button>

                    <AgentOpinions />
                </div>

            </div>

        </div>
    )
}

export default TokenPage;