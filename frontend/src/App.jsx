import React, { useState, useRef, useEffect } from 'react';

const ChatMessage = ({ isUser, content, isLoading, error }) => (
  <div className={`flex mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
    <div className={`rounded-lg px-4 py-2 max-w-[80%] ${
      isUser 
        ? 'bg-blue-600 text-white' 
        : error 
          ? 'bg-red-100 text-red-600'
          : 'bg-gray-100 text-gray-900'
    }`}>
      {isLoading ? (
        <div className="flex items-center gap-2">
          <div className="animate-spin h-4 w-4 border-2 border-blue-600 rounded-full border-t-transparent"/>
          <span className="text-sm">TechnicIA réfléchit...</span>
        </div>
      ) : (
        <p className="text-sm whitespace-pre-wrap">{content}</p>
      )}
    </div>
  </div>
);

export default function App() {
  const [messages, setMessages] = useState([
    {
      isUser: false,
      content: "Bonjour ! Je suis TechnicIA, votre assistant technique. Comment puis-je vous aider ?"
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    
    // Ajoute le message de l'utilisateur
    setMessages(prev => [...prev, { isUser: true, content: userMessage }]);
    
    // Ajoute un message "en cours" temporaire
    setMessages(prev => [...prev, { 
      isUser: false, 
      content: '', 
      isLoading: true 
    }]);
    
    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ query: userMessage })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (!data.response) {
        throw new Error('Réponse invalide du serveur');
      }
      
      // Remplace le message "en cours" par la vraie réponse
      setMessages(prev => [
        ...prev.slice(0, -1),
        { isUser: false, content: data.response }
      ]);

    } catch (error) {
      console.error('Erreur lors de la requête:', error);
      
      // Remplace le message "en cours" par un message d'erreur
      setMessages(prev => [
        ...prev.slice(0, -1),
        { 
          isUser: false, 
          content: "Désolé, une erreur s'est produite lors de la communication avec le serveur. Veuillez réessayer.", 
          error: true 
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 flex items-center justify-center">
      <div className="w-full max-w-2xl bg-white rounded-lg shadow-lg flex flex-col h-[600px]">
        {/* Header */}
        <div className="border-b p-4">
          <h1 className="text-xl font-semibold">TechnicIA Demo</h1>
        </div>
        
        {/* Messages */}
        <div className="flex-1 p-4 overflow-auto">
          <div className="space-y-4">
            {messages.map((message, index) => (
              <ChatMessage 
                key={index}
                isUser={message.isUser}
                content={message.content}
                isLoading={message.isLoading}
                error={message.error}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input */}
        <div className="border-t p-4">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Posez votre question..."
              className="flex-1 px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={isLoading}
            />
            <button 
              type="submit" 
              className={`px-4 py-2 rounded-lg transition-colors ${
                isLoading || !input.trim()
                  ? 'bg-gray-300 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white'
              }`}
              disabled={isLoading || !input.trim()}
            >
              {isLoading ? 'Envoi...' : 'Envoyer'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}