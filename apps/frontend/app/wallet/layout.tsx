import Navbar from '@/components/Navbar'
import Image from 'next/image'
import React from 'react'

const layout = ({ children }: { children: React.ReactNode }) => {
    return (
        <div className="w-full h-screen flex justify-end">
            {/* Fixed left column */}
            <div
                className="w-1/4 fixed top-0 left-0 h-screen z-10 landingLeft"
                style={{
                    backgroundImage: `url('/landing-left-bg.jpg')`
                }}
            >   
                <div className="w-1/4 h-screen fixed">
                    {/* Our logo in top left */}
                    <div className="absolute top-8 left-8 flex flex-col items-left">
                        <Image
                            src="/icons/lmk-logo.svg"
                            alt="Logo"
                            width={100}
                            height={75}
                            className="mt-1 mb-2 drop-shadow-lg"
                        />
                        <span className="text-lg leading-snug text-white font-medium drop-shadow-md claimText">
                            let me know <br />
                            when to&nbsp;
                            <span className="claimOptions relative">
                                <span className="claimOption option-buy">buy</span>
                                <span className="claimOption option-hold">hold</span>
                                <span className="claimOption option-sell">sell</span>
                            </span>
                        </span>
                    </div>


                    {/* ETH Bucharest & Powered by logos in bottom left */}
                    <div className="absolute bottom-8 left-8 flex flex-col items-left uppercase ">
                        <span className="text-sm text-white font-medium drop-shadow-md tracking-widest">
                            powered by
                        </span>
                        <Image
                            src="/icons/tokenmetrics-white.svg"
                            alt="Token Metrics"
                            width={110}
                            height={44}
                            className="mt-1 mb-1 tokeMetricsLogo"
                        />
                        <Image
                            src="/icons/coinbase-white.svg"
                            alt="Coinbase Wallet"
                            width={110}
                            height={44}
                            className="mt-1 mb-10 coinBaseWalletLogo"
                        />


                        <span className="text-sm text-white font-medium drop-shadow-md tracking-widest">
                            developed during
                        </span>
                        <Image
                            src="/icons/eth_bucharest_logo.png"
                            alt="ETH Bucharest Logo"
                            width={150}
                            height={55}
                            className="mt-1 ethBucharestLogo drop-shadow-lg"
                        />
                    </div>
                </div>
                <div className="feathers">
                        <div className="feather feather-1"></div>
                        <div className="feather feather-2"></div>
                        <div className="feather feather-3"></div>
                    </div>





            </div>

            {/* Scrollable content area with padding to account for fixed sidebar */}
            <div className=" w-3/4 min-h-screen z-20">
                <div className="px-10 py-4 w-full">
                    <Navbar />
                    {children}
                </div>
            </div>
        </div>
    )
}

export default layout