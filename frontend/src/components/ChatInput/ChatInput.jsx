import { useEffect, useRef } from 'react';
import './ChatInput.css';

function ChatInput({ value, onChange, onSend, disabled }) {
  const textareaRef = useRef(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`;
  }, [value]);

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  return (
    <div className="chat-input-wrap">
      <textarea
        ref={textareaRef}
        rows={1}
        className="chat-input"
        placeholder="Message ChatAI..."
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />
      <button type="button" className="send-button" onClick={onSend} disabled={disabled || !value.trim()}>
        Send
      </button>
    </div>
  );
}

export default ChatInput;
