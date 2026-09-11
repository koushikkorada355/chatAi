import { useRef } from 'react';
import './Navbar.css';

function Navbar({ activeConversation, onLogout, onUploadDocument, uploadDisabled = false }) {
  const fileInputRef = useRef(null);

  const handleUploadClick = () => {
    if (!uploadDisabled) {
      fileInputRef.current?.click();
    }
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (file) {
      onUploadDocument?.(file);
    }
    event.target.value = '';
  };

  return (
    <header className="navbar">
      <div className="navbar-title-wrap">
        <span className="navbar-badge">Chat</span>
        <h2 className="navbar-title">{activeConversation ? activeConversation.title : 'New conversation'}</h2>
      </div>

      <div className="navbar-actions">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          className="hidden-file-input"
          onChange={handleFileChange}
        />

        <button type="button" className="upload-button" onClick={handleUploadClick} disabled={uploadDisabled}>
          {uploadDisabled ? 'Uploading...' : 'Upload PDF'}
        </button>

        <button type="button" className="logout-button" onClick={onLogout}>
          Logout
        </button>
      </div>
    </header>
  );
}

export default Navbar;
