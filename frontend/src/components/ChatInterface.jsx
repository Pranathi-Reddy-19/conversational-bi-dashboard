import React, { useState, useRef, useEffect, useContext } from 'react';
import axios from 'axios';
import { AuthContext } from '../context/AuthContext';
import ChartRenderer from './ChartRenderer';
import './ChatInterface.css';

export default function ChatInterface({ currentDataset }) {
  const { user } = useContext(AuthContext);
  const [messages, setMessages] = useState([]);
  const [inputMsg, setInputMsg] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [lastSql, setLastSql] = useState(null);
  const [summaryQueries, setSummaryQueries] = useState([]);
  const [isSummaryLoading, setIsSummaryLoading] = useState(false);
  const [isSummaryOpen, setIsSummaryOpen] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Generate session ID if not exists
    let sid = sessionStorage.getItem('session_id');
    if (!sid) {
      sid = crypto.randomUUID();
      sessionStorage.setItem('session_id', sid);
    }
    setSessionId(sid);
    
    // Load history
    if (user?.username && sid) {
      axios.get(`http://localhost:8000/api/history/${user.username}/${sid}`)
        .then(res => setMessages(res.data.messages || []))
        .catch(console.error);
    }
  }, [user]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  
  useEffect(() => scrollToBottom(), [messages, isLoading]);

  useEffect(() => {
    if (user?.username && currentDataset) {
      setIsSummaryLoading(true);
      setSummaryQueries([]);
      setIsSummaryOpen(false);
      
      axios.post('http://localhost:8000/api/summary', {
        username: user.username,
        filename: currentDataset
      })
      .then(res => {
        if (res.data.queries) {
          setSummaryQueries(res.data.queries);
        }
      })
      .catch(console.error)
      .finally(() => setIsSummaryLoading(false));
    } else {
      setSummaryQueries([]);
    }
  }, [user, currentDataset]);

  const handleSend = async (msgText) => {
    if (!msgText.trim() || !currentDataset || isLoading) return;

    const userMsg = { role: 'user', content: msgText };
    setMessages(prev => [...prev, userMsg]);
    setInputMsg('');
    setIsLoading(true);

    try {
      const res = await axios.post('http://localhost:8000/api/chat', {
        username: user.username,
        session_id: sessionId,
        message: msgText,
        last_sql: lastSql
      });

      if (res.data.error) {
        setMessages(prev => [...prev, { role: 'assistant', content: res.data.error }]);
      } else {
        const aiMsg = {
          role: 'assistant',
          content: res.data.content,
          queries: res.data.queries,
          follow_ups: res.data.follow_ups
        };
        setMessages(prev => [...prev, aiMsg]);
        if (res.data.last_sql) {
          setLastSql(res.data.last_sql);
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'An API error occurred.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="messages-area">
        {!currentDataset && (
          <div className="empty-state">
            👈 Please securely upload or select a dataset from the sidebar to initialize the dashboard.
          </div>
        )}

        {currentDataset && (summaryQueries.length > 0 || isSummaryLoading) && (
          <div className="summary-section glass-panel" style={{marginBottom: '20px', padding: '15px'}}>
            <div 
              style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer'}}
              onClick={() => setIsSummaryOpen(!isSummaryOpen)}
            >
              <h3 style={{margin: 0, fontSize: '1.2rem', color: 'var(--text-primary)'}}>📊 Automatic Dataset Summary</h3>
              <span style={{color: 'var(--text-secondary)'}}>{isSummaryOpen ? '▲' : '▼'}</span>
            </div>
            
            {isSummaryOpen && (
              <div style={{marginTop: '15px'}}>
                {isSummaryLoading ? (
                  <div className="typing-indicator">Analyzing dataset & building overview charts...</div>
                ) : (
                  summaryQueries.map((q, qIdx) => (
                    <ChartRenderer key={qIdx} queryInfo={q} />
                  ))
                )}
              </div>
            )}
          </div>
        )}
        
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role === 'user' ? 'user' : 'assistant glass-panel'}`}>
            <div 
              className="msg-content" 
              dangerouslySetInnerHTML={{ __html: m.content }} 
            />
            {m.queries && m.queries.map((q, qIdx) => (
              <ChartRenderer key={qIdx} queryInfo={q} />
            ))}
            {m.follow_ups && i === messages.length - 1 && (
              <div className="follow-ups">
                <strong style={{color: 'var(--text-muted)', fontSize: '0.9rem'}}>💡 Suggested Follow-ups:</strong>
                <div className="follow-up-buttons">
                  {m.follow_ups.map((fq, fqIdx) => (
                    <button 
                      key={fqIdx} 
                      className="btn follow-up-btn"
                      onClick={() => handleSend(fq)}
                    >
                      {fq}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
        {isLoading && (
          <div className="chat-bubble assistant glass-panel">
            <span className="typing-indicator">Analyzing data...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area glass-panel">
        <input 
          type="text" 
          value={inputMsg}
          onChange={(e) => setInputMsg(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend(inputMsg)}
          placeholder="Ask a question about your dataset..."
          disabled={!currentDataset}
        />
        <button 
          className="btn btn-primary" 
          onClick={() => handleSend(inputMsg)}
          disabled={!currentDataset || isLoading}
        >
          Send
        </button>
      </div>
    </div>
  );
}
