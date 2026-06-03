import SwiftUI
import Combine

@MainActor
class ConversationStore: ObservableObject {
    @Published var messages: [ChatMessage] = []
    @Published var currentConversationId: UUID?
    @Published var isSaving: Bool = false

    func addMessage(_ message: ChatMessage) {
        messages.append(message)
    }

    func updateMessageFeedback(messageId: UUID, wasHelpful: Bool) {
        if let idx = messages.firstIndex(where: { $0.id == messageId }) {
            messages[idx].feedbackGiven = wasHelpful
        }
    }

    func clearMessages() {
        messages = []
        currentConversationId = nil
    }

    func loadConversation(_ conversation: CachedConversation) {
        messages = conversation.messages.map { cachedMsg in
            ChatMessage(
                id: cachedMsg.id,
                role: cachedMsg.role,
                content: cachedMsg.content,
                memoryIds: cachedMsg.memoryIds,
                feedbackGiven: cachedMsg.feedbackGiven
            )
        }
        currentConversationId = conversation.id
    }

    func saveCurrentConversation() async {
        guard !messages.isEmpty else { return }
        isSaving = true

        let savedId = await CacheService.shared.saveConversation(
            messages: messages,
            conversationId: currentConversationId
        )
        currentConversationId = savedId
        isSaving = false
    }
}
