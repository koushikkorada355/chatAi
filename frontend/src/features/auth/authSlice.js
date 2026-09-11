import { createSlice } from '@reduxjs/toolkit';
import { setAuthToken } from '../../services/api';

const getStoredToken = () => localStorage.getItem('chatai_token');
const getStoredUser = () => {
  const rawUser = localStorage.getItem('chatai_user');
  try {
    return rawUser ? JSON.parse(rawUser) : null;
  } catch (error) {
    return null;
  }
};

const initialState = {
  token: getStoredToken(),
  user: getStoredUser(),
  isAuthenticated: Boolean(getStoredToken()),
  loading: false,
  error: null,
};

const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    loginSuccess: (state, action) => {
      const { token, user } = action.payload;
      state.token = token;
      state.user = user;
      state.isAuthenticated = true;
      state.error = null;
      localStorage.setItem('chatai_token', token);
      if (user) {
        localStorage.setItem('chatai_user', JSON.stringify(user));
      }
      setAuthToken(token);
    },
    setUser: (state, action) => {
      state.user = action.payload;
      localStorage.setItem('chatai_user', JSON.stringify(action.payload));
    },
    logout: (state) => {
      state.token = null;
      state.user = null;
      state.isAuthenticated = false;
      localStorage.removeItem('chatai_token');
      localStorage.removeItem('chatai_user');
      setAuthToken(null);
    },
    setAuthLoading: (state, action) => {
      state.loading = action.payload;
    },
    setAuthError: (state, action) => {
      state.error = action.payload;
    },
    clearAuthError: (state) => {
      state.error = null;
    },
  },
});

export const {
  loginSuccess,
  setUser,
  logout,
  setAuthLoading,
  setAuthError,
  clearAuthError,
} = authSlice.actions;

export default authSlice.reducer;
