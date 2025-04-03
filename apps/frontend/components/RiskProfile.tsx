import { useEffect, useState } from "react";
import axios from "axios";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "./ui/dialog";
import { Button } from "./ui/button";
import { axiosInstance } from "@/axios";
type RiskProfile = "HIGH_RISK" | "BALANCED" | "SAFE";

const riskProfiles: RiskProfile[] = [
    "HIGH_RISK",
    "BALANCED",
    "SAFE",
];

const RiskProfile = ({ address }: { address: string }) => {
    const [open, setOpen] = useState(false);
    const [riskProfile, setRiskProfile] = useState<RiskProfile>("BALANCED");

    const getPreferences = async () => {
        try {

            const res = await axiosInstance.get(`/wallets/${address}`);
            console.log('res', res.data);
            if (res.data.risk_profile) {
                setRiskProfile(res.data.risk_profile);
            }
        } catch (error) {
            if (axios.isAxiosError(error) && error.response?.status === 404) {
                setOpen(true);
            }
        }
    }

    const updatePreferences = async () => {
        try {
            const res = await axiosInstance.post(`/wallets`, {
                address: address,
                risk_profile: riskProfile,
            });
            console.log('res', res.data);
            setOpen(false);
        } catch (error) {
            console.log('error', error);
        }
    }

    const onRiskProfileChange = (profile: RiskProfile) => {
        setRiskProfile(profile);
    }

    useEffect(() => {
        getPreferences();
    }, []);

    return (
        <Dialog open={open} onOpenChange={setOpen}>
            <DialogContent>
                <DialogHeader>
                    <DialogTitle>Configure your risk profile</DialogTitle>
                    <DialogDescription className="flex justify-center pt-8">
                        <div className="flex gap-4">
                            {riskProfiles.map((profile, index) => (
                                <div
                                    onClick={() => onRiskProfileChange(profile)}
                                    key={index} className={`shadow-md p-4 rounded-md cursor-pointer ${riskProfile === profile ? "border-[1px] border-sky-800" : ""}`}>
                                    <p className="text-center font-bold text-sky-800">
                                        {profile}
                                    </p>
                                </div>
                            ))}
                        </div>

                    </DialogDescription>
                </DialogHeader>
                <DialogFooter>
                    <Button onClick={updatePreferences}>Save</Button>
                </DialogFooter>
            </DialogContent>
        </Dialog >
    )
}

export default RiskProfile;