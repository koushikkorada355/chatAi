import './ChatMessage.css';

function ChatMessage({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`chat-message-row ${isUser ? 'user-row' : 'assistant-row'}`}>
      <div className={`chat-message-bubble ${isUser ? 'user' : 'assistant'}`}>
        <p>{message.content}</p>
      </div>
    </div>
  );
}

export default ChatMessage;
