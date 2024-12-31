import React, { useState } from 'react';
import { FileText, Send, Upload } from 'lucide-react';

const API_URL = 'http://localhost:8000';

const App = () => {
  const [file, setFile] = useState(null);
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !file.name.endsWith('.pdf')) {
      alert('Veuillez sélectionner un fichier PDF');
      return;
    }

    setUploading(true);
    setFile(file);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_URL}/api/index/file`, {
        method: 'POST',
        body: formData
      });
      const result = await response.json();
      
      if (result.status === 'success') {
        setMessages(prev => [...prev, {
          type: 'system',
          content: `Document ${file.name} indexé avec succès`
        }]);
      } else {
        throw new Error(result.error);
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Erreur lors de l'indexation: ${error.message}`
      }]);
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setMessages(prev => [...prev, { type: 'user', content: query }]);

    try {
      const response = await fetch(`${API_URL}/api/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      });
      
      const result = await response.json();
      setMessages(prev => [...prev, { 
        type: 'assistant',
        content: result.answer,
        sources: result.sources
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        type: 'error',
        content: `Erreur: ${error.message}`
      }]);
    } finally {
      setLoading(false);
      setQuery('');
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-100">
      <header className="bg-white shadow-sm p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-xl font-bold text-gray-800">TechnicIA Demo</h1>
          <div className="flex items-center gap-2">
            <label className="relative cursor-pointer">
              <input
                type="file"
                className="hidden"
                accept=".pdf"
                onChange={handleFileUpload}
                disabled={uploading}
              />
              <div className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                <Upload className="w-4 h-4" />
                {uploading ? 'Indexation...' : 'Charger PDF'}
              </div>
            </label>
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`p-4 rounded-lg ${
                msg.type === 'user'
                  ? 'bg-blue-500 text-white ml-12'
                  : msg.type === 'assistant'
                  ? 'bg-white shadow-sm'
                  : msg.type === 'error'
                  ? 'bg-red-100 text-red-700'
                  : 'bg-gray-100'
              }`}
            >
              <div className="prose max-w-none">
                {msg.content}
              </div>
              
              {msg.sources && msg.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-200">
                  <details className="text-sm text-gray-600">
                    <summary className="cursor-pointer hover:text-gray-900">
                      Sources ({msg.sources.length})
                    </summary>
                    <ul className="mt-2 space-y-1">
                      {msg.sources.map((source, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <FileText className="w-4 h-4 mt-1 shrink-0" />
                          <span>
                            Page {source.payload.page_number}:{' '}
                            {source.payload.text.substring(0, 100)}...
                          </span>
                        </li>
                      ))}
                    </ul>
                  </details>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white border-t p-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="flex gap-2">
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Posez votre question..."
              className="flex-1 rounded-lg border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              disabled={loading || !file}
            />
            <button
              type="submit"
              disabled={loading || !file || !query.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default App;