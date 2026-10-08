const configuredApiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
const apiBaseUrl = (configuredApiBaseUrl || 'http://localhost:8000').replace(/\/+$/, '');

export const API_URL = `${apiBaseUrl}/api`;
