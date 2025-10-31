/**
 * Mock WebSocket Service for Testing
 */

import { vi } from 'vitest'

class MockWebSocketService {
  constructor() {
    this.listeners = new Map()
    this.connected = false
  }

  connect = vi.fn(() => {
    this.connected = true
    this.emit('connect', {})
  })

  disconnect = vi.fn(() => {
    this.connected = false
    this.emit('disconnect', {})
  })

  on = vi.fn((event, callback) => {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, [])
    }
    this.listeners.get(event).push(callback)
  })

  off = vi.fn((event, callback) => {
    if (!this.listeners.has(event)) return
    const callbacks = this.listeners.get(event)
    const index = callbacks.indexOf(callback)
    if (index > -1) {
      callbacks.splice(index, 1)
    }
  })

  emit(event, data) {
    if (!this.listeners.has(event)) return
    this.listeners.get(event).forEach((callback) => callback(data))
  }

  // Helper to simulate WebSocket events
  simulateEvent(event, data) {
    this.emit(event, data)
  }

  // Helper to simulate chapter generation progress
  simulateChapterProgress(chapterId, stage, progress) {
    this.emit('chapter_generation_progress', {
      chapter_id: chapterId,
      stage,
      progress,
      message: `Stage ${stage}: ${progress}%`,
    })
  }

  // Helper to simulate PDF processing progress
  simulatePdfProgress(pdfId, stage, progress) {
    this.emit('pdf_processing_progress', {
      pdf_id: pdfId,
      stage,
      progress,
      message: `Stage ${stage}: ${progress}%`,
    })
  }

  reset() {
    this.listeners.clear()
    this.connected = false
    this.connect.mockClear()
    this.disconnect.mockClear()
    this.on.mockClear()
    this.off.mockClear()
  }
}

export const mockWebSocketService = new MockWebSocketService()
export default mockWebSocketService
