"use client";

import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { useParams } from 'next/navigation'
import React from 'react'

const TokenPage = () => {
    const { wallet, token } = useParams();
    return (
        <div className='h-full w-full'>
            <div className='flex justify-start items-center py-4'>
                <Button asChild variant="outline">
                    <Link href={`/wallet/${wallet}`}>Back</Link>
                </Button>

            </div>

        </div>
    )
}

export default TokenPage;