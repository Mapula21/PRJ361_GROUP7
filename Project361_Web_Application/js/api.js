// Project361 API helper
// Connects the web dashboard to Sandra/Lindo's Flask API.

import { auth } from "./firebase-config.js";

export const API_BASE_URL = "http://127.0.0.1:5000";

// The current backend uses the demo athlete record (ID 1).
// Later, this can be replaced with a Firebase-user-to-athlete mapping.
export const ATHLETE_ID = 1;

async function getAuthHeaders() {
    const user = auth.currentUser;

    if (!user) {
        throw new Error("You are not logged in.");
    }

    const token = await user.getIdToken();

    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
    };
}

async function apiRequest(path, options = {}) {
    const headers = await getAuthHeaders();

    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        headers: {
            ...headers,
            ...(options.headers || {})
        }
    });

    let data = {};
    try {
        data = await response.json();
    } catch (_) {
        // Keep the original status error if the response is not JSON.
    }

    if (!response.ok) {
        throw new Error(data.message || `API request failed (${response.status})`);
    }

    return data;
}

export async function getAnalytics() {
    return apiRequest(`/analytics?athlete_id=${ATHLETE_ID}`);
}

export async function getAlerts() {
    return apiRequest(`/alerts?athlete_id=${ATHLETE_ID}`);
}

export async function getHistory() {
    return apiRequest(`/history?athlete_id=${ATHLETE_ID}`);
}

export async function getAthlete() {
    return apiRequest(`/athlete?athlete_id=${ATHLETE_ID}`);
}

export async function sendChatMessage(message) {
    return apiRequest("/chat", {
        method: "POST",
        body: JSON.stringify({
            athlete_id: ATHLETE_ID,
            message
        })
    });
}
