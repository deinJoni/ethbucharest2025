"use client";

import { useEffect, useState } from "react";
import axios from "axios";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "./ui/dialog";
import { RadioGroup, RadioGroupItem } from "./ui/radio-group";
import { Label } from "./ui/label";
import { Button } from "./ui/button";

const riskProfiles = [
  {
    id: 1,
    value: "SAFE",
    name: "Conservative",
    description: "Lower risk, stable returns",
    emoji: "🧘",
    color: "green",
  },
  {
    id: 2,
    value: "BALANCED",
    name: "Moderate",
    description: "Balanced risk and return",
    emoji: "🏄",
    color: "yellow",
  },
  {
    id: 3,
    value: "HIGH_RISK",
    name: "Aggressive",
    description: "Higher risk, higher potential",
    emoji: "🚀",
    color: "red",
  },
];

const Preferences = ({ address }: { address: string }) => {
  const [open, setOpen] = useState(false);
  const [riskProfile, setRiskProfile] = useState<
    "SAFE" | "BALANCED" | "HIGH_RISK"
  >("BALANCED");
  const [selectedProfileId, setSelectedProfileId] = useState<number>(2);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const updatePreferences = async () => {
    try {
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/wallets`,
        {
          address: address,
        },
        {
          headers: {
            "X-Skip-Browser-Warning": "true",
            "ngrok-skip-browser-warning": "69420",
          },
        }
      );
      if (!res.data.risk_profile) {
        setOpen(true);
      }
    } catch (error) {
      console.log("error", error);
    }
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      console.log("Submitting preferences:", riskProfile);
      const res = await axios.post(
        `${process.env.NEXT_PUBLIC_API_URL}/wallets`,
        {
          address: address,
          risk_profile: riskProfile,
        },
        {
          headers: {
            "X-Skip-Browser-Warning": "true",
            "ngrok-skip-browser-warning": "69420",
          },
        }
      );
      setOpen(false);
    } catch (error) {
      console.error("Error saving preferences:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    updatePreferences();
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md md:max-w-xl p-6">
        <DialogHeader className="mb-6">
          <DialogTitle className="text-2xl font-bold text-center">
            Choose Your Investment Style
          </DialogTitle>
          <DialogDescription className="text-center text-muted-foreground mt-2">
            Select the risk profile that best matches your investment goals
          </DialogDescription>
        </DialogHeader>

        <div className="py-4">
          <RadioGroup
            value={selectedProfileId.toString()}
            onValueChange={(val) => {
              const profileId = Number(val);
              setSelectedProfileId(profileId);
              const profile = riskProfiles.find((p) => p.id === profileId);
              if (profile) {
                setRiskProfile(
                  profile.value as "SAFE" | "BALANCED" | "HIGH_RISK"
                );
              }
            }}
            className="grid grid-cols-1 md:grid-cols-3 gap-4"
          >
            {riskProfiles.map((profile) => {
              const isSelected = selectedProfileId === profile.id;

              return (
                <div key={profile.id} className="relative">
                  <RadioGroupItem
                    value={profile.id.toString()}
                    id={`r${profile.id}`}
                    className="sr-only"
                  />
                  <Label
                    htmlFor={`r${profile.id}`}
                    className="cursor-pointer block h-full"
                  >
                    <div
                      className={`
                        relative rounded-xl overflow-hidden transition-all duration-200
                        ${
                          isSelected
                            ? "ring-2 ring-offset-2"
                            : "hover:shadow-md"
                        }
                        ${
                          profile.id === 1
                            ? "ring-green-500"
                            : profile.id === 2
                            ? "ring-amber-500"
                            : "ring-rose-500"
                        }
                      `}
                    >
                      <div
                        className={`
                        h-full p-6 flex flex-col items-center justify-between
                        ${
                          isSelected
                            ? profile.id === 1
                              ? "bg-green-50"
                              : profile.id === 2
                              ? "bg-amber-50"
                              : "bg-rose-50"
                            : "bg-card hover:bg-muted/50"
                        }
                      `}
                      >
                        <div className="flex flex-col items-center text-center">
                          <div
                            className={`
                            text-4xl mb-3 transform transition-transform duration-200
                            ${isSelected ? "scale-110" : ""}
                          `}
                          >
                            {profile.emoji}
                          </div>
                          <h3
                            className={`
                            font-semibold text-lg mb-1
                            ${
                              isSelected
                                ? profile.id === 1
                                  ? "text-green-700"
                                  : profile.id === 2
                                  ? "text-amber-700"
                                  : "text-rose-700"
                                : "text-foreground"
                            }
                          `}
                          >
                            {profile.name}
                          </h3>
                          <p className="text-sm text-muted-foreground">
                            {profile.description}
                          </p>
                        </div>

                        {isSelected && (
                          <div
                            className={`
                              absolute top-3 right-3 w-5 h-5 rounded-full flex items-center justify-center
                              ${
                                profile.id === 1
                                  ? "bg-green-500"
                                  : profile.id === 2
                                  ? "bg-amber-500"
                                  : "bg-rose-500"
                              }
                            `}
                          >
                            <svg
                              xmlns="http://www.w3.org/2000/svg"
                              width="12"
                              height="12"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="3"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              className="text-white"
                            >
                              <polyline points="20 6 9 17 4 12"></polyline>
                            </svg>
                          </div>
                        )}
                      </div>
                    </div>
                  </Label>
                </div>
              );
            })}
          </RadioGroup>
        </div>

        <DialogFooter className="mt-6">
          <Button
            onClick={handleSubmit}
            className="w-full"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Saving..." : "Save Preferences"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default Preferences;
