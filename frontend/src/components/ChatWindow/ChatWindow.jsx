import { useEffect, useRef } from 'react';
import ChatMessage from '../ChatMessage/ChatMessage';
import './ChatWindow.css';

function ChatWindow({ messages, isAiTyping }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isAiTyping]);

  return (
    <div className="chat-window">
      <div className="chat-messages">
        {messages.length === 0 ? (
          <div className="empty-chat">Start a new conversation</div>
        ) : (
          messages.map((message) => <ChatMessage key={message.id ?? `${message.role}-${message.created_at}`} message={message} />)
        )}

        {isAiTyping && (
          <div className="typing-bubble">
            <span />
            <span />
            <span />
          </div>
        )}

        <div ref={endRef} />
      </div>
    </div>
  );
}

export default ChatWindow;
