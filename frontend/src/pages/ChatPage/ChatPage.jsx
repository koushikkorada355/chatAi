import { useEffect, useMemo, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import Sidebar from '../../components/Sidebar/Sidebar';
import Navbar from '../../components/Navbar/Navbar';
import ChatWindow from '../../components/ChatWindow/ChatWindow';
import ChatInput from '../../components/ChatInput/ChatInput';
import {
  setConversationsLoading,
  setConversationsError,
  setConversations,
  addConversation,
  setActiveConversationId,
  clearConversations,
} from '../../features/conversations/conversationsSlice';
import {
  setMessages,
  setChatInput,
  setAiTyping,
  appendUserMessage,
  appendAssistantMessage,
  setChatLoading,
  setChatError,
} from '../../features/chat/chatSlice';
import {
  createConversation,
  getConversations,
  getMessages,
  sendChatMessage,
  uploadDocument,
} from '../../services/api';
import { logout } from '../../features/auth/authSlice';
import './ChatPage.css';

function ChatPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState('');

  const { token } = useSelector((state) => state.auth);
  const { conversations, activeConversationId } = useSelector((state) => state.conversations);
  const { messages, input, isAiTyping, loading } = useSelector((state) => state.chat);

  const activeConversation = useMemo(
    () => conversations.find((conv) => conv.id === activeConversationId) || null,
    [conversations, activeConversationId]
  );

  const fetchConversations = async () => {
    if (!token) return;

    dispatch(setConversationsLoading(true));
    try {
      const { data } = await getConversations();
      dispatch(setConversations(data));

      if (data.length > 0) {
        const nextActive = activeConversationId && data.some((item) => item.id === activeConversationId)
          ? activeConversationId
          : data[0].id;
        dispatch(setActiveConversationId(nextActive));
      } else {
        dispatch(setActiveConversationId(null));
      }
    } catch (error) {
      dispatch(setConversationsError(error?.response?.data?.detail || 'Failed to load conversations.'));
    } finally {
      dispatch(setConversationsLoading(false));
    }
  };

  const fetchMessages = async (convId) => {
    if (!convId) {
      dispatch(setMessages({ conversationId: null, messages: [] }));
      return;
    }

    dispatch(setChatLoading(true));
    try {
      const { data } = await getMessages(convId);
      dispatch(setMessages({ conversationId: convId, messages: data }));
    } catch (error) {
      dispatch(setChatError(error?.response?.data?.detail || 'Failed to load messages.'));
    } finally {
      dispatch(setChatLoading(false));
    }
  };

  useEffect(() => {
    if (!token) {
      dispatch(clearConversations());
      return;
    }

    fetchConversations();
  }, [token]);

  useEffect(() => {
    if (!activeConversationId) {
      dispatch(setMessages({ conversationId: null, messages: [] }));
      dispatch(setAiTyping(false));
      return;
    }

    dispatch(setAiTyping(false));
    fetchMessages(activeConversationId);
  }, [activeConversationId]);

  const handleCreateConversation = async () => {
    try {
      const response = await createConversation(`New chat ${conversations.length + 1}`);
      const newConversation = response.data;
      dispatch(addConversation(newConversation));
      dispatch(setActiveConversationId(newConversation.id));
      dispatch(setMessages({ conversationId: newConversation.id, messages: [] }));
    } catch (error) {
      dispatch(setConversationsError(error?.response?.data?.detail || 'Failed to create a new chat.'));
    }
  };

  const handleSelectConversation = (convId) => {
    dispatch(setActiveConversationId(convId));
  };

  const handleUploadDocument = async (file) => {
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    setUploading(true);
    setUploadStatus('');

    try {
      const { data } = await uploadDocument(formData);
      setUploadStatus(`Uploaded "${data.filename}" successfully. ${data.chunks_created} chunks indexed.`);
    } catch (error) {
      setUploadStatus(error?.response?.data?.detail || 'Failed to upload PDF.');
    } finally {
      setUploading(false);
    }
  };

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || !activeConversationId || isAiTyping) return;

    const uniqueId = `temp-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const tempUserMessage = {
      id: uniqueId,
      conversation_id: activeConversationId,
      role: 'user',
      content: trimmed,
      created_at: new Date().toISOString(),
    };

    dispatch(appendUserMessage({ conversationId: activeConversationId, message: tempUserMessage }));
    dispatch(setChatInput(''));
    dispatch(setAiTyping(true));

    try {
      const { data } = await sendChatMessage(activeConversationId, trimmed);
      const assistantMessage = data?.message ?? data;
      dispatch(appendAssistantMessage({ conversationId: activeConversationId, message: assistantMessage }));
    } catch (error) {
      const errorId = `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      dispatch(
        appendAssistantMessage({
          conversationId: activeConversationId,
          message: {
            id: errorId,
            conversation_id: activeConversationId,
            role: 'assistant',
            content: 'Sorry, I could not respond right now. Please try again.',
            created_at: new Date().toISOString(),
          },
        })
      );
    } finally {
      dispatch(setAiTyping(false));
    }
  };

  const handleLogout = () => {
    navigate('/login');
    dispatch(logout());
  };

  return (
    <div className="chatpage-shell">
      <Sidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onCreateConversation={handleCreateConversation}
      />

      <div className="chat-main-panel">
        <Navbar
          activeConversation={activeConversation}
          onLogout={handleLogout}
          onUploadDocument={handleUploadDocument}
          uploadDisabled={uploading}
        />

        <div className="chat-content">
          {uploadStatus && <div className="upload-status">{uploadStatus}</div>}

          <ChatWindow messages={messages} isAiTyping={isAiTyping} />

          <ChatInput
            value={input}
            onChange={(value) => dispatch(setChatInput(value))}
            onSend={handleSend}
            disabled={isAiTyping || !activeConversationId || loading}
          />
        </div>
      </div>
    </div>
  );
}

export default ChatPage;
