"use client"
import { useRouter } from 'next/navigation';
import { useAccount } from 'wagmi';
import { useEffect } from 'react';
import { Avatar, Name } from '@coinbase/onchainkit/identity';
import { ConnectWallet } from '@coinbase/onchainkit/wallet';
export default function App() {

  const router = useRouter();
  const { address } = useAccount();

  useEffect(() => {
    if (address) {
      router.push(`/wallet/${address}`);
    }
  }, [address]);

  return (
    <div
      className='h-screen grid grid-cols-2 min-h-full'>
      <div className='bg-cover bg-center w-full h-full' style={{ backgroundImage: `url('/landing-left-bg.jpg')` }}></div>
      <div className='h-full w-full flex items-center justify-center'>
        <div className="flex flex-col justify-center items-center text-center gap-2">
          <span className=''>Hit the button below to get started</span>
          <ConnectWallet
            className='bg-sky-900 hover:bg-sky-800 rounded-sm border-[1px] border-sky-900 text-red-500 min-w-[350px] text-center py-5'
          >
          </ConnectWallet>
          <span className='text-sm'>
            Use your wn current account or set one up via Base SmartWallet
          </span>
        </div>
      </div>
    </div>
  );
}