'use client'
import { useState, useRef } from 'react'
import { toast } from 'sonner'
import { TextArea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { useStore } from '@/store'
import useAIChatStreamHandler from '@/hooks/useAIStreamHandler'
import { useQueryState } from 'nuqs'
import Icon from '@/components/ui/icon'

const ChatInput = () => {
  const { chatInputRef } = useStore()

  const { handleStreamResponse } = useAIChatStreamHandler()
  const [selectedAgent] = useQueryState('agent')
  const [teamId] = useQueryState('team')
  const [inputMessage, setInputMessage] = useState('')
  const [selectedImages, setSelectedImages] = useState<string[]>([])
  const fileInputRef = useRef<HTMLInputElement>(null)
  const isStreaming = useStore((state) => state.isStreaming)

  const handleImageSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.currentTarget.files
    if (!files) return

    for (let i = 0; i < files.length; i++) {
      const file = files[i]

      // Validate file type
      if (!file.type.startsWith('image/')) {
        toast.error('Only image files are supported')
        continue
      }

      // Validate file size (5MB limit)
      if (file.size > 5 * 1024 * 1024) {
        toast.error(`Image ${file.name} exceeds 5MB limit`)
        continue
      }

      // Convert to base64
      const reader = new FileReader()
      reader.onload = (event) => {
        const base64 = event.target?.result as string
        setSelectedImages((prev) => [...prev, base64])
      }
      reader.onerror = () => {
        toast.error(`Failed to read ${file.name}`)
      }
      reader.readAsDataURL(file)
    }

    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeImage = (index: number) => {
    setSelectedImages((prev) => prev.filter((_, i) => i !== index))
  }

  const handleSubmit = async () => {
    if (!inputMessage.trim() && selectedImages.length === 0) return

    // If images are uploaded but no message provided, use default message
    let currentMessage = inputMessage.trim()
    if (!currentMessage && selectedImages.length > 0) {
      currentMessage = 'Show me recipes based on these ingredients'
    }

    const currentImages = selectedImages
    setInputMessage('')
    setSelectedImages([])

    try {
      await handleStreamResponse(currentMessage, currentImages)
    } catch (error) {
      toast.error(
        `Error in handleSubmit: ${
          error instanceof Error ? error.message : String(error)
        }`
      )
    }
  }

  return (
    <div className="relative mx-auto mb-1 w-full max-w-2xl font-geist">
      {/* Image Preview Section */}
      {selectedImages.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2 rounded-lg border border-accent bg-primaryAccent p-3">
          {selectedImages.map((image, index) => (
            <div key={index} className="relative inline-block">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={image}
                alt={`Selected ${index + 1}`}
                className="h-16 w-16 rounded border border-accent object-cover"
              />
              <button
                onClick={() => removeImage(index)}
                className="absolute -right-2 -top-2 rounded-full bg-red-500 p-1 text-white hover:bg-red-600"
              >
                <Icon type="x" color="white" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input Section */}
      <div className="flex w-full items-end justify-center gap-x-2">
        <TextArea
          placeholder="Ask anything or attach images"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyDown={(e) => {
            if (
              e.key === 'Enter' &&
              !e.nativeEvent.isComposing &&
              !e.shiftKey &&
              !isStreaming
            ) {
              e.preventDefault()
              handleSubmit()
            }
          }}
          className="w-full border border-accent bg-primaryAccent px-4 text-sm text-primary focus:border-accent"
          disabled={!(selectedAgent || teamId)}
          ref={chatInputRef}
        />

        <div className="flex gap-x-1">
          {/* Image Upload Button */}
          <Button
            onClick={() => fileInputRef.current?.click()}
            disabled={!(selectedAgent || teamId) || isStreaming}
            size="icon"
            className="rounded-xl bg-gray-500 p-5 text-primaryAccent hover:bg-gray-600"
            title="Attach images"
          >
            <Icon type="plus-icon" color="primaryAccent" />
          </Button>

          {/* Send Button */}
          <Button
            onClick={handleSubmit}
            disabled={
              !(selectedAgent || teamId) ||
              (!inputMessage.trim() && selectedImages.length === 0) ||
              isStreaming
            }
            size="icon"
            className="rounded-xl bg-primary p-5 text-primaryAccent"
          >
            <Icon type="send" color="primaryAccent" />
          </Button>
        </div>

        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept="image/*"
          onChange={handleImageSelect}
          className="hidden"
          disabled={!(selectedAgent || teamId) || isStreaming}
        />
      </div>
    </div>
  )
}

export default ChatInput
