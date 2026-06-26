import axios from 'axios';

// Since we setup the proxy in vite.config.js, we can just point to /api if running in dev
// But for robustness in this demo, let's allow an override
const BASE_URL = 'http://localhost:8000';

export const analyzeMath = async (expression, action = 'solve') => {
    try {
        const response = await axios.post(`${BASE_URL}/analyze`, {
            expression,
            action
        });
        return response.data;
    } catch (error) {
        console.error("API Error", error);
        throw error;
    }
};
