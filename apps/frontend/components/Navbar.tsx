'use client'
import {
    ConnectWallet,
    Wallet,
    WalletDropdown,
    WalletDropdownLink,
    WalletDropdownDisconnect,
} from '@coinbase/onchainkit/wallet';
import {
    Address,
    Avatar,
    Name,
    Identity,
    EthBalance,
} from '@coinbase/onchainkit/identity';
import { ModeToggle } from './ModeToggle';
import { usePathname } from 'next/navigation';
import useProfileStore from '@/store/profile';
import { Loader2 } from 'lucide-react';

const Navbar = () => {
    const pathname = usePathname();
    const { profile } = useProfileStore();

    if (pathname === '/') return null;

    return (
        <div className="flex w-full items-center justify-between p-4 shadow-md h-[75px] rounded-lg">
            {/* <ModeToggle /> */}
            <div className="flex items-center gap-2">
                {profile.name ? (
                    <p className="text-2xl font-bold text-sky-800">
                        Hello, {profile.name} 🙌
                    </p>
                ) : (
                    <Loader2 className="w-6 h-6 animate-spin" />
                )}
            </div>
            <Wallet>
                <ConnectWallet>
                    <Avatar className="h-6 w-6" />
                    <Name />
                </ConnectWallet>
                <WalletDropdown>
                    <Identity className="px-4 pt-3 pb-2" hasCopyAddressOnClick>
                        <Avatar />
                        <Name />
                        <Address />
                        <EthBalance />
                    </Identity>
                    <WalletDropdownLink
                        icon="wallet"
                        href="https://keys.coinbase.com"
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Wallet
                    </WalletDropdownLink>
                    <WalletDropdownDisconnect />
                </WalletDropdown>
            </Wallet>
        </div>
    )
}

export default Navbar;