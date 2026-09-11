import './Sidebar.css';

function Sidebar({ conversations, activeConversationId, onSelectConversation, onCreateConversation }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="brand-mark">C</div>
        <div>
          <p className="brand-label">ChatAI</p>
        </div>
      </div>

      <button type="button" className="new-chat-button" onClick={onCreateConversation}>
        + New Chat
      </button>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="empty-state">No chats yet</div>
        ) : (
          conversations.map((conversation) => (
            <button
              key={conversation.id}
              type="button"
              className={`conversation-item ${conversation.id === activeConversationId ? 'active' : ''}`}
              onClick={() => onSelectConversation(conversation.id)}
            >
              <span className="conversation-title">{conversation.title}</span>
              <span className="conversation-meta">{new Date(conversation.updated_at || conversation.created_at).toLocaleDateString()}</span>
            </button>
          ))
        )}
      </div>
    </aside>
  );
}

export default Sidebar;
