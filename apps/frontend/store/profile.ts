// zustand store for profile

import { create } from 'zustand';

interface ProfileState {
    profile: {
        name: string;
    };
    setProfile: (profile: { name: string }) => void;
}

const useProfileStore = create<ProfileState>((set) => ({
    profile: {
        name: '',
    },
    setProfile: (profile: { name: string }) => set({ profile }),
}));

export default useProfileStore;