import { useEffect, useRef, useState } from 'react'

export const useWebSocket = (url) => {
  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState(null)
  const ws = useRef(null)
  const reconnectTimeout = useRef(null)

  useEffect(() => {
    const connect = () => {
      const wsUrl = url || `ws://${window.location.host}/ws/scrape-progress`
      ws.current = new WebSocket(wsUrl)

      ws.current.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        
        const pingInterval = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send('ping')
          }
        }, 30000)

        ws.current.pingInterval = pingInterval
      }

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          setLastMessage(data)
        } catch (e) {
          console.log('WebSocket message:', event.data)
        }
      }

      ws.current.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        
        if (ws.current?.pingInterval) {
          clearInterval(ws.current.pingInterval)
        }

        reconnectTimeout.current = setTimeout(() => {
          console.log('Reconnecting WebSocket...')
          connect()
        }, 3000)
      }

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error)
        ws.current?.close()
      }
    }

    connect()

    return () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current)
      }
      if (ws.current?.pingInterval) {
        clearInterval(ws.current.pingInterval)
      }
      ws.current?.close()
    }
  }, [url])

  return { isConnected, lastMessage }
}
