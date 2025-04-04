import axios from "axios";

export const axiosInstance = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL,
    headers: {
        'X-Skip-Browser-Warning': 'true',
        "ngrok-skip-browser-warning": "69420",
        'Access-Control-Allow-Origin': '*',
    },
    withCredentials: false
});