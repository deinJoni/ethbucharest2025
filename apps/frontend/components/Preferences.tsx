import { useEffect, useState } from "react";
import axios from "axios";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "./ui/dialog";

const riskProfiles = [
    {
        id: 1,
        name: "Conservative",
    },
    {
        id: 2,
        name: "Moderate",
    },
    {
        id: 3,
        name: "Aggressive",
    },
];

const Preferences = ({ address }: { address: string }) => {
    const [open, setOpen] = useState(false);
    const [riskProfile, setRiskProfile] = useState<1 | 2 | 3>(2);

    const [preferences, setPreferences] = useState({
        preferences: {
            theme: "light",
        }
    });

    const updatePreferences = async () => {
        try {
            // const res = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/wallets/${address}`, {
            const res = await axios.post(`${process.env.NEXT_PUBLIC_API_URL}/wallets`, {
                address: address,
                // risk_profile
            }, {
                headers: {
                    'X-Skip-Browser-Warning': 'true',
                    "ngrok-skip-browser-warning": "69420",
                },
            });
            if (!res.data.risk_profile) {
                setOpen(true);
            }
        } catch (error) {
            console.log('error', error);
        }
    }

    useEffect(() => {
        updatePreferences();
        // getPreferences();
    }, []);

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Are you absolutely sure?</DialogTitle>
                    <DialogDescription className="flex justify-center">
                        <div className="flex">
                            {/* <RadioGroup defaultValue="comfortable">
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="default" id="r1" />
                                    <Label htmlFor="r1">Default</Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="comfortable" id="r2" />
                                    <Label htmlFor="r2">Comfortable</Label>
                                </div>
                                <div className="flex items-center space-x-2">
                                    <RadioGroupItem value="compact" id="r3" />
                                    <Label htmlFor="r3">Compact</Label>
                                </div>
                            </RadioGroup> */}
                            {riskProfiles.map((profile) => (
                                <div key={profile.id} className="shadow-md p-4 rounded-md">
                                    {profile.name}
                                </div>
                            ))}
                        </div>
                    </DialogDescription>
                </DialogHeader>
            </DialogContent>
        </Dialog >
    )
}

export default Preferences;