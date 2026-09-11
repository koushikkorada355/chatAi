import { configureStore } from '@reduxjs/toolkit';
import authReducer from './features/auth/authSlice';
import conversationsReducer from './features/conversations/conversationsSlice';
import chatReducer from './features/chat/chatSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    conversations: conversationsReducer,
    chat: chatReducer,
  },
});
