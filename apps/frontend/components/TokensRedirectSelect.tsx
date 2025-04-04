import { useRouter } from "next/navigation";
import { useParams } from "next/navigation";
import { useState } from "react";
import tokensData from "@/data/tokens.json";
import { Button } from "@/components/ui/button";
import {
    Command,
    CommandEmpty,
    CommandGroup,
    CommandInput,
    CommandItem,
    CommandList,
} from "@/components/ui/command";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { ChevronsUpDown } from "lucide-react";

const TokenRedirectSelect = () => {
    const router = useRouter();
    const params = useParams();
    const [openCombobox, setOpenCombobox] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");

    // Filter tokens based on search query
    const filteredTokens = tokensData.filter(
        (token) =>
            token.token_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            token.token_symbol.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Handle token selection and redirect
    const handleTokenSelect = (tokenId: string) => {
        const selectedToken = tokensData.find(t => t.token_id.toString() === tokenId);

        if (selectedToken) {
            // Close the combobox
            setOpenCombobox(false);

            // Get the wallet address from params
            const address = params.wallet;

            // Redirect to the token page with the required params
            router.push(`/wallet/${address}/token/discover_token_address?id=${selectedToken.token_id}&name=${selectedToken.token_name}`);
        }
    };

    return (
        <div className="w-full">
            <div className="flex items-center gap-3 w-full">
                <div className="flex-1 w-full">
                    <Popover open={openCombobox} onOpenChange={setOpenCombobox}>
                        <PopoverTrigger asChild>
                            <Button
                                variant="outline"
                                role="combobox"
                                aria-expanded={openCombobox}
                                className="w-full justify-between h-11"
                            >
                                Search for a token...
                                <ChevronsUpDown className="opacity-50 ml-2 h-4 w-4" />
                            </Button>
                        </PopoverTrigger>
                        <PopoverContent className="w-[calc(100vw-2rem)] sm:w-[calc(100%-2rem)] p-0" align="start" sideOffset={4}>
                            <Command shouldFilter={false} className="w-full">
                                <CommandInput
                                    placeholder="Search tokens..."
                                    className="h-9 w-full"
                                    value={searchQuery}
                                    onValueChange={setSearchQuery}
                                />
                                <CommandList className="w-full">
                                    <CommandEmpty>No tokens found.</CommandEmpty>
                                    <CommandGroup>
                                        {filteredTokens.slice(0, 50).map((token) => (
                                            <CommandItem
                                                key={token.token_id}
                                                value={token.token_id.toString()}
                                                onSelect={(value) => {
                                                    handleTokenSelect(value);
                                                }}
                                                className="w-full"
                                            >
                                                <div className="flex flex-col">
                                                    <span>{token.token_name}</span>
                                                    <span className="text-sm text-gray-500">
                                                        {token.token_symbol}
                                                    </span>
                                                </div>
                                            </CommandItem>
                                        ))}
                                    </CommandGroup>
                                </CommandList>
                            </Command>
                        </PopoverContent>
                    </Popover>
                </div>
            </div>

            <p className="mt-4 text-sm text-gray-500">
                Select a token to view its detailed information page
            </p>
        </div>
    );
};

export default TokenRedirectSelect;