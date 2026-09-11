import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  conversations: [],
  activeConversationId: null,
  loading: false,
  error: null,
};

const conversationsSlice = createSlice({
  name: 'conversations',
  initialState,
  reducers: {
    setConversationsLoading: (state, action) => {
      state.loading = action.payload;
    },
    setConversationsError: (state, action) => {
      state.error = action.payload;
    },
    setConversations: (state, action) => {
      state.conversations = action.payload;
      state.error = null;
    },
    addConversation: (state, action) => {
      const newConversation = action.payload;
      const exists = state.conversations.some((conv) => conv.id === newConversation.id);
      if (!exists) {
        state.conversations.unshift(newConversation);
      }
    },
    setActiveConversationId: (state, action) => {
      state.activeConversationId = action.payload;
    },
    updateConversationTitle: (state, action) => {
      const { id, title } = action.payload;
      const target = state.conversations.find((item) => item.id === id);
      if (target) {
        target.title = title;
      }
    },
    clearConversations: (state) => {
      state.conversations = [];
      state.activeConversationId = null;
      state.error = null;
    },
  },
});

export const {
  setConversationsLoading,
  setConversationsError,
  setConversations,
  addConversation,
  setActiveConversationId,
  updateConversationTitle,
  clearConversations,
} = conversationsSlice.actions;

export default conversationsSlice.reducer;
