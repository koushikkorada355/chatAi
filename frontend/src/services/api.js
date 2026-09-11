import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'https://chatai-6p1l.onrender.com',
  headers: {
    'Content-Type': 'application/json',
  },
});

const getStoredToken = () => localStorage.getItem('chatai_token');

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = {
      ...config.headers,
      Authorization: `Bearer ${token}`,
    };
  }
  return config;
});

export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common.Authorization;
  }
};

export const login = (payload) => api.post('/auth/login', payload);
export const signup = (payload) => api.post('/auth/signup', payload);
export const loginUser = login;
export const signupUser = signup;
export const createConversation = (title) => api.post('/conversations/', { title });
export const getConversations = () => api.get('/conversations/');
export const getMessages = (conversationId) => api.get(`/conversations/${conversationId}/messages`);
export const sendChatMessage = (conversationId, content) => api.post(`/conversations/${conversationId}/chat`, { content });
export const uploadDocument = (formData) => api.post('/documents/upload', formData, {
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

export default api;
