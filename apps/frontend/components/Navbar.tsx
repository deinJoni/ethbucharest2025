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

const Navbar = () => {
    const pathname = usePathname();

    if (pathname === '/') return null;

    return (
            <div className="flex w-full items-center justify-end p-4 shadow-md h-[75px]">
                {/* <ModeToggle /> */}
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