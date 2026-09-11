import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  messagesByConversation: {}, // Messages keyed by conversation ID
  messages: [], // Current conversation messages (for backward compatibility)
  input: '',
  isAiTyping: false,
  loading: false,
  error: null,
  messageIdCounter: 0, // For generating unique IDs
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setMessages: (state, action) => {
      const { conversationId, messages } = action.payload;
      state.messages = messages;
      if (conversationId) {
        state.messagesByConversation[conversationId] = messages;
      }
      state.error = null;
      state.isAiTyping = false;
    },
    appendUserMessage: (state, action) => {
      const { conversationId, message } = action.payload;
      state.messages.push(message);
      if (conversationId) {
        if (!state.messagesByConversation[conversationId]) {
          state.messagesByConversation[conversationId] = [];
        }
        state.messagesByConversation[conversationId].push(message);
      }
    },
    appendAssistantMessage: (state, action) => {
      const { conversationId, message } = action.payload;
      state.messages.push(message);
      if (conversationId) {
        if (!state.messagesByConversation[conversationId]) {
          state.messagesByConversation[conversationId] = [];
        }
        state.messagesByConversation[conversationId].push(message);
      }
    },
    setChatInput: (state, action) => {
      state.input = action.payload;
    },
    clearChatInput: (state) => {
      state.input = '';
    },
    setAiTyping: (state, action) => {
      state.isAiTyping = action.payload;
    },
    setChatLoading: (state, action) => {
      state.loading = action.payload;
    },
    setChatError: (state, action) => {
      state.error = action.payload;
    },
    resetChat: (state) => {
      state.messages = [];
      state.input = '';
      state.isAiTyping = false;
      state.loading = false;
      state.error = null;
    },
    clearChatForConversation: (state, action) => {
      const conversationId = action.payload;
      state.messages = [];
      state.isAiTyping = false;
      state.input = '';
      state.error = null;
      if (conversationId && state.messagesByConversation[conversationId]) {
        delete state.messagesByConversation[conversationId];
      }
    },
    generateMessageId: (state) => {
      state.messageIdCounter += 1;
      return state.messageIdCounter;
    },
  },
});

export const {
  setMessages,
  appendUserMessage,
  appendAssistantMessage,
  setChatInput,
  clearChatInput,
  setAiTyping,
  setChatLoading,
  setChatError,
  resetChat,
  clearChatForConversation,
  generateMessageId,
} = chatSlice.actions;

export default chatSlice.reducer;
