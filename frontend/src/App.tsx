import { useState } from 'react'
import './App.css'

interface Message {
  id: number
  text: string
  sender: 'user' | 'bot'
}

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputText, setInputText] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSend = async () => {
    if (!inputText.trim()) return

    const userMessage: Message = {
      id: Date.now(),
      text: inputText,
      sender: 'user'
    }

    setMessages(prev => [...prev, userMessage])
    setInputText('')
    setIsLoading(true)

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: inputText }),
      })

      const data = await response.json()

      const botMessage: Message = {
        id: Date.now() + 1,
        text: data.response,
        sender: 'bot'
      }

      setMessages(prev => [...prev, botMessage])
    } catch (error) {
      console.error('Error:', error)
      const errorMessage: Message = {
        id: Date.now() + 1,
        text: '서버와의 연결에 실패했습니다.',
        sender: 'bot'
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>똑소리 - 소비자 분쟁 조정 챗봇</h1>
      </header>

      <div className="chat-container">
        <div className="messages-area">
          {messages.length === 0 ? (
            <div className="empty-state">
              <p>안녕하세요! 소비자 분쟁 관련 질문을 해주세요.</p>
            </div>
          ) : (
            messages.map(msg => (
              <div key={msg.id} className={`message ${msg.sender}`}>
                <div className="message-content">
                  {msg.text}
                </div>
              </div>
            ))
          )}
          {isLoading && (
            <div className="message bot">
              <div className="message-content loading">
                답변을 생성하고 있습니다...
              </div>
            </div>
          )}
        </div>

        <div className="input-area">
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="질문을 입력하세요..."
            disabled={isLoading}
          />
          <button onClick={handleSend} disabled={isLoading || !inputText.trim()}>
            전송
          </button>
        </div>
      </div>
    </div>
  )
}

export default App
