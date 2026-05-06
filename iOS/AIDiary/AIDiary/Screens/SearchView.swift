import SwiftUI

// 单条对话消息
struct ChatMessage: Identifiable {
    let id = UUID()
    let role: String  // "user" 或 "assistant"
    let content: String
    var memoryIds: [Int] = []
    var feedbackGiven: Bool? = nil
}

struct SearchView: View {
    @State private var query = ""
    @State private var isSearching = false
    @State private var chatMessages: [ChatMessage] = []  // 完整对话历史
    @State private var currentMemoryIds: [Int] = []  // 当前回答的 memory IDs
    @State private var currentFeedback: Bool? = nil  // 当前回答的反馈状态

    var body: some View {
        VStack(spacing: 0) {
            statusBarPlaceholder

            searchBox

            if isSearching && chatMessages.isEmpty {
                // 首次加载状态
                loadingView
            } else if chatMessages.isEmpty {
                // 空状态 - 显示快捷问题
                contentSection
            } else {
                // 对话历史
                chatHistoryView
            }
        }
    }

    private var statusBarPlaceholder: some View {
        Color.clear.frame(height: 62)
    }

    private var searchBox: some View {
        HStack(spacing: 8) {
            Text("🔍")
                .font(.system(size: 18))

            TextField("问我任何问题", text: $query)
                .font(.system(size: 15))
                .foregroundColor(Color(hex: "1A1918"))
                .onSubmit {
                    askAI()
                }

            if !query.isEmpty {
                Button {
                    query = ""
                } label: {
                    Text("✕")
                        .font(.system(size: 16))
                        .foregroundColor(Color(hex: "9C9B99"))
                }
            }
        }
        .padding(.horizontal, 16)
        .frame(height: 48)
        .background(Color.white)
        .cornerRadius(12)
        .overlay(
            RoundedRectangle(cornerRadius: 12)
                .stroke(Color(hex: "E5E4E1"), lineWidth: 1)
        )
        .padding(.horizontal, 16)
        .padding(.top, 16)
    }

    private var loadingView: some View {
        VStack(spacing: 12) {
            Spacer()
            ProgressView()
                .tint(Color(hex: "C4935A"))
            Text("AI 思考中...")
                .foregroundColor(Color(hex: "9C9B99"))
            Spacer()
        }
    }

    private var chatHistoryView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 16) {
                    ForEach(chatMessages) { message in
                        ChatMessageView(message: message) { wasHelpful in
                            sendFeedback(for: message.id, wasHelpful: wasHelpful)
                        }
                    }

                    // 底部操作按钮
                    if !isSearching {
                        Button {
                            startNewChat()
                        } label: {
                            Text("开始新对话")
                                .font(.system(size: 14))
                                .foregroundColor(Color(hex: "C4935A"))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 12)
                                .background(Color(hex: "C4935A").opacity(0.1))
                                .cornerRadius(12)
                        }
                        .padding(.top, 8)
                    }
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 100)
            }
            .onChange(of: chatMessages.count) { _, _ in
                // 自动滚动到底部
                if let lastMessage = chatMessages.last {
                    withAnimation {
                        proxy.scrollTo(lastMessage.id, anchor: .bottom)
                    }
                }
            }
        }
    }

    private var contentSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("快捷问题")
                .font(.system(size: 14, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))
                .padding(.top, 24)

            HStack(spacing: 8) {
                QuickQuestionChip(question: "最近开心的事") {
                    query = "最近开心的事"
                    askAI()
                }
                QuickQuestionChip(question: "工作相关的日记") {
                    query = "工作相关的日记"
                    askAI()
                }
            }

            HStack(spacing: 8) {
                QuickQuestionChip(question: "这周的情绪变化") {
                    query = "这周的情绪变化"
                    askAI()
                }
                QuickQuestionChip(question: "和朋友的活动") {
                    query = "和朋友的活动"
                    askAI()
                }
            }
        }
        .padding(.horizontal, 16)
    }

    // MARK: - Actions

    private func askAI() {
        guard !query.isEmpty else { return }
        isSearching = true

        // 构建 API 需要的对话历史格式
        let apiHistory = chatMessages.map { ["role": $0.role, "content": $0.content] }

        Task {
            do {
                let response = try await APIService.shared.askQuestion(
                    question: query,
                    conversationHistory: apiHistory.isEmpty ? nil : apiHistory
                )
                await MainActor.run {
                    // 添加用户消息
                    chatMessages.append(ChatMessage(role: "user", content: query))
                    // 添加 AI 回答
                    let aiMessage = ChatMessage(
                        role: "assistant",
                        content: response.answer,
                        memoryIds: response.memoryIds ?? []
                    )
                    chatMessages.append(aiMessage)
                    currentMemoryIds = response.memoryIds ?? []
                    currentFeedback = nil
                    isSearching = false
                    query = ""
                }
            } catch {
                await MainActor.run {
                    chatMessages.append(ChatMessage(role: "user", content: query))
                    chatMessages.append(ChatMessage(role: "assistant", content: "抱歉，AI 思考时遇到了问题。请稍后再试。"))
                    isSearching = false
                    query = ""
                }
            }
        }
    }

    private func sendFeedback(for messageId: UUID, wasHelpful: Bool) {
        // 找到对应消息的 memory IDs
        guard let message = chatMessages.first(where: { $0.id == messageId }),
              !message.memoryIds.isEmpty else { return }

        Task {
            do {
                try await APIService.shared.sendFeedback(memoryIds: message.memoryIds, wasHelpful: wasHelpful)
                await MainActor.run {
                    if let idx = chatMessages.firstIndex(where: { $0.id == messageId }) {
                        chatMessages[idx].feedbackGiven = wasHelpful
                    }
                }
            } catch {
                // 静默处理
                await MainActor.run {
                    if let idx = chatMessages.firstIndex(where: { $0.id == messageId }) {
                        chatMessages[idx].feedbackGiven = wasHelpful
                    }
                }
            }
        }
    }

    private func startNewChat() {
        chatMessages = []
        currentMemoryIds = []
        currentFeedback = nil
    }
}

// MARK: - Chat Message View

struct ChatMessageView: View {
    let message: ChatMessage
    let onFeedback: (Bool) -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            // 消息内容
            HStack(alignment: .top, spacing: 8) {
                if message.role == "assistant" {
                    Text("🤖")
                        .font(.system(size: 18))
                }

                Text(message.content)
                    .font(.system(size: 15))
                    .foregroundColor(Color(hex: "1A1918"))
                    .lineSpacing(6)
            }
            .padding(14)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(message.role == "user" ? Color(hex: "F5F4F0") : Color.white)
            .cornerRadius(14)

            // AI 回答的反馈按钮
            if message.role == "assistant" && !message.memoryIds.isEmpty {
                if let feedback = message.feedbackGiven {
                    HStack(spacing: 6) {
                        Image(systemName: feedback ? "checkmark.circle.fill" : "info.circle.fill")
                            .font(.system(size: 12))
                            .foregroundColor(feedback ? Color(hex: "3D8A5A") : Color(hex: "D08068"))
                        Text(feedback ? "感谢反馈" : "已收到")
                            .font(.system(size: 12))
                            .foregroundColor(Color(hex: "9C9B99"))
                    }
                    .padding(.leading, 14)
                } else {
                    HStack(spacing: 16) {
                        Button {
                            onFeedback(true)
                        } label: {
                            HStack(spacing: 4) {
                                Image(systemName: "hand.thumbsup")
                                    .font(.system(size: 12))
                                Text("有帮助")
                                    .font(.system(size: 12))
                            }
                            .foregroundColor(Color(hex: "6D6C6A"))
                        }

                        Button {
                            onFeedback(false)
                        } label: {
                            HStack(spacing: 4) {
                                Image(systemName: "hand.thumbsdown")
                                    .font(.system(size: 12))
                                Text("没帮助")
                                    .font(.system(size: 12))
                            }
                            .foregroundColor(Color(hex: "6D6C6A"))
                        }
                    }
                    .padding(.leading, 14)
                }
            }
        }
    }
}

struct QuickQuestionChip: View {
    let question: String
    let action: () -> Void

    init(question: String, action: @escaping () -> Void = {}) {
        self.question = question
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            Text(question)
                .font(.system(size: 13))
                .foregroundColor(Color(hex: "6D6C6A"))
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .background(Color.white)
                .cornerRadius(16)
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(Color(hex: "E5E4E1"), lineWidth: 1)
                )
        }
    }
}

#Preview {
    ContentView()
}