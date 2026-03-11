import React, { useContext, useState, useEffect } from 'react';
import axios from 'axios';
import { AuthContext } from './context/AuthContext';
import Auth from './components/Auth';
import Sidebar from './components/Sidebar';
import ChatInterface from './components/ChatInterface';

function App() {
  const { user } = useContext(AuthContext);
  const [datasets, setDatasets] = useState([]);
  const [currentDataset, setCurrentDataset] = useState(null);
  const [kpis, setKpis] = useState([]);

  useEffect(() => {
    if (user?.username) {
      axios.get(`http://localhost:8000/api/datasets/${user.username}`)
        .then(res => {
          setDatasets(res.data.datasets || []);
          setCurrentDataset(res.data.current);
          setKpis(res.data.kpis || []);
        })
        .catch(err => {
          console.error("Failed to load datasets, session might be empty:", err);
          setCurrentDataset(null);
        });
    }
  }, [user]);

  const handleDatasetChange = async (filename) => {
    try {
      const res = await axios.post('http://localhost:8000/api/datasets/switch', {
        username: user.username,
        filename
      });
      setCurrentDataset(res.data.current);
      setKpis(res.data.kpis || []);
    } catch (err) {
      console.error(err);
    }
  };

  const handleUploadComplete = (data) => {
    setDatasets(data.datasets);
    setCurrentDataset(data.filename);
    setKpis(data.kpis || []);
  };

  if (!user) {
    return <Auth />;
  }

  return (
    <div className="app-container">
      <Sidebar 
        datasets={datasets} 
        currentDataset={currentDataset} 
        onDatasetChange={handleDatasetChange}
        onUploadComplete={handleUploadComplete}
      />
      <main className="main-content">
        <ChatInterface currentDataset={currentDataset} />
      </main>
    </div>
  );
}

export default App;
