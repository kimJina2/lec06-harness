/**
 * SSE 스트리밍 유틸리티
 * FastAPI의 StreamingResponse(media_type="text/event-stream") 를 읽어 처리합니다.
 */
export async function readSSEStream({ url, body, onChunk, onDone, onError }) {
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const data = JSON.parse(line.slice(6))
          if (data.error) { onError?.(data.error); return }
          if (data.chunk) onChunk?.(data.chunk)
          if (data.done)  onDone?.(data.full)
        } catch { /* partial JSON, skip */ }
      }
    }
  } catch (e) {
    onError?.(e.message)
  }
}
