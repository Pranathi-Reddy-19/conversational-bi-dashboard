import React, { useRef, useState } from 'react';
import axios from 'axios';
import { useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import './Sidebar.css';

export default function Sidebar({ datasets, currentDataset, onDatasetChange, onUploadComplete }) {
  const { user, logout } = useContext(AuthContext);
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    formData.append('username', user.username);

    try {
      const res = await axios.post('http://localhost:8000/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      onUploadComplete(res.data);
    } catch (err) {
      console.error('Upload failed:', err);
      alert('Upload failed. Check console for details.');
    } finally {
      setIsUploading(false);
      e.target.value = null; // reset
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2 style={{ fontSize: '1.5rem', fontWeight: 800 }}>📉 Lakshya BI</h2>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Hello, {user?.username}</div>
      </div>

      <div className="sidebar-content">
        <div className="upload-zone glass-panel" onClick={handleUploadClick}>
          {isUploading ? 'Uploading...' : '📂 Click to Upload CSV'}
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            accept=".csv"
            style={{ display: 'none' }}
          />
        </div>

        <div className="datasets-section">
          <h3 className="section-title">Uploaded Files</h3>
          {datasets?.length === 0 && (
            <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
              No datasets uploaded yet.
            </div>
          )}
          {datasets?.map((ds, idx) => (
            <button 
              key={idx}
              className={`dataset-btn ${currentDataset === ds ? 'active' : ''}`}
              onClick={() => onDatasetChange(ds)}
            >
              📄 {ds}
            </button>
          ))}
        </div>
      </div>

      <div className="sidebar-footer">
        <button onClick={logout} className="btn" style={{width: '100%', borderColor: 'var(--border)'}}>
          Logout
        </button>
      </div>
    </div>
  );
}
