"use client";

import { useParams } from 'next/navigation'
import React from 'react'

const TokenPage = () => {
    const { wallet, token } = useParams();
    // console.log(wallet, token);
    return (
        <div>token page</div>
    )
}

export default TokenPage;