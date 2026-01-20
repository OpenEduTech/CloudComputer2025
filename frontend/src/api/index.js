import axios from 'axios';

// Configure Axios (Base URL handled by Vite proxy)
const api = axios.create({
  // baseURL: 'http://localhost:8000', // Optional if proxy is set
});

export const createTask = async (keyword, params = {}) => {
  const response = await api.post('/api/task', { keyword, params });
  return response.data;
};

export const getTaskStatus = async (taskId) => {
  const response = await api.get(`/api/task/${taskId}/status`);
  return response.data;
};

export const getGraphData = async (nodeId, depth = 2) => {
  const response = await api.get(`/api/graph/${encodeURIComponent(nodeId)}`, {
    params: { depth }
  });
  return response.data;
};

export default api;
