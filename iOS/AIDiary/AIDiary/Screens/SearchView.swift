import SwiftUI

// 单条对话消息
struct ChatMessage: Identifiable, Equatable {
    let id = UUID()
    let role: String  // "user" 或 "assistant"
    let content: String
    var memoryIds: [Int] = []
    var feedbackGiven: Bool? = nil

    static func == (lhs: ChatMessage, rhs: ChatMessage) -> Bool {
        lhs.id == rhs.id
    }
}

struct SearchView: View {
    @State private var query = ""
    @State private var isSearching = false
    @State private var chatMessages: [ChatMessage] = []
    @FocusState private var isInputFocused: Bool

    // 键盘高度（用于调整布局）
    @State private var keyboardHeight: CGFloat = 0

    var body: some View {
        VStack(spacing: 0) {
            // 顶部导航栏
            navigationBar

            // 对话内容区域
            if chatMessages.isEmpty && !isSearching {
                // 空状态
                emptyStateView
            } else {
                // 对话历史
                chatHistoryView
            }

            // 底部输入栏
            bottomInputBar
        }
        .onAppear {
            // 监听键盘
            NotificationCenter.default.addObserver(forName: UIResponder.keyboardWillShowNotification, object: nil, queue: .main) { notification in
                if let keyboardFrame = notification.userInfo?[UIResponder.keyboardFrameEndUserInfoKey] as? CGRect {
                    keyboardHeight = keyboardFrame.height
                }
            }
            NotificationCenter.default.addObserver(forName: UIResponder.keyboardWillHideNotification, object: nil, queue: .main) { _ in
                keyboardHeight = 0
            }
        }
    }

    // MARK: - 顶部导航栏
    private var navigationBar: some View {
        HStack {
            Text("AI 助手")
                .font(.system(size: 17, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))

            Spacer()

            if !chatMessages.isEmpty {
                Button {
                    startNewChat()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "plus.circle")
                            .font(.system(size: 14))
                        Text("新对话")
                            .font(.system(size: 14))
                    }
                    .foregroundColor(Color(hex: "C4935A"))
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color(hex: "C4935A").opacity(0.1))
                    .cornerRadius(16)
                }
            }
        }
        .padding(.horizontal, 16)
        .padding(.top, 62) // 状态栏
        .padding(.bottom, 12)
        .background(Color(hex: "FAF9F6"))
    }

    // MARK: - 空状态视图
    private var emptyStateView: some View {
        VStack(spacing: 0) {
            Spacer()

            // Logo 或图标
            Text("🌰")
                .font(.system(size: 60))
                .padding(.bottom, 16)

            Text("问我任何问题")
                .font(.system(size: 20, weight: .medium))
                .foregroundColor(Color(hex: "1A1918"))
                .padding(.bottom, 8)

            Text("我可以帮你回顾日记、分析情绪、查找记忆")
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "9C9B99"))
                .multilineTextAlignment(.center)
                .padding(.bottom, 32)

            // 快捷问题
            VStack(spacing: 12) {
                HStack(spacing: 10) {
                    QuickQuestionButton(question: "最近开心的事") {
                        query = "最近开心的事"
                        askAI()
                    }
                    QuickQuestionButton(question: "工作相关的日记") {
                        query = "工作相关的日记"
                        askAI()
                    }
                }
                HStack(spacing: 10) {
                    QuickQuestionButton(question: "这周的情绪变化") {
                        query = "这周的情绪变化"
                        askAI()
                    }
                    QuickQuestionButton(question: "和朋友的活动") {
                        query = "和朋友的活动"
                        askAI()
                    }
                }
            }
            .padding(.horizontal, 16)

            Spacer()
            Spacer()
        }
        .frame(maxWidth: .infinity)
    }

    // MARK: - 对话历史视图
    private var chatHistoryView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 16) {
                    ForEach(chatMessages) { message in
                        ChatBubbleView(message: message) { wasHelpful in
                            sendFeedback(for: message.id, wasHelpful: wasHelpful)
                        }
                        .id(message.id)
                    }

                    // 正在输入指示器
                    if isSearching {
                        HStack(spacing: 8) {
                            Text("🤖")
                                .font(.system(size: 18))

                            HStack(spacing: 4) {
                                ForEach(0..<3) { i in
                                    Circle()
                                        .fill(Color(hex: "C4935A"))
                                        .frame(width: 6, height: 6)
                                        .scaleEffect(isSearching ? 1.0 : 0.5)
                                        .animation(
                                            Animation.easeInOut(duration: 0.6)
                                                .repeatForever()
                                                .delay(Double(i) * 0.2),
                                            value: isSearching
                                        )
                                }
                            }
                            .padding(.leading, 8)
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                        .id("typing")
                    }
                }
                .padding(.horizontal, 16)
                .padding(.top, 16)
                .padding(.bottom, 16)
            }
            .background(Color(hex: "FAF9F6"))
            .onChange(of: chatMessages.count) { _, _ in
                // 滚动到最新消息
                if isSearching {
                    withAnimation {
                        proxy.scrollTo("typing", anchor: .bottom)
                    }
                } else if let lastMessage = chatMessages.last {
                    withAnimation {
                        proxy.scrollTo(lastMessage.id, anchor: .bottom)
                    }
                }
            }
        }
    }

    // MARK: - 底部输入栏
    private var bottomInputBar: some View {
        HStack(spacing: 12) {
            // 输入框
            HStack(spacing: 8) {
                TextField("问我任何问题...", text: $query)
                    .font(.system(size: 15))
                    .foregroundColor(Color(hex: "1A1918"))
                    .focused($isInputFocused)
                    .onSubmit {
                        askAI()
                    }

                if !query.isEmpty {
                    Button {
                        query = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 16))
                            .foregroundColor(Color(hex: "C4C4C4"))
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.white)
            .cornerRadius(24)
            .shadow(color: Color.black.opacity(0.05), radius: 4, y: 2)

            // 发送按钮
            Button {
                askAI()
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 36))
                    .foregroundColor(query.isEmpty ? Color(hex: "D4D4D4") : Color(hex: "C4935A"))
            }
            .disabled(query.isEmpty || isSearching)
        }
        .padding(.horizontal, 16)
        .padding(.top, 12)
        .padding(.bottom, max(keyboardHeight > 0 ? 8 : 24, safeAreaBottom))
        .background(Color(hex: "FAF9F6"))
    }

    // 安全区域底部高度
    private var safeAreaBottom: CGFloat {
        if #available(iOS 15.0, *) {
            return 0
        }
        return 34
    }

    // MARK: - Actions

    private func askAI() {
        guard !query.isEmpty, !isSearching else { return }
        isSearching = true
        isInputFocused = false

        let currentQuery = query
        query = ""

        // 构建 API 需要的对话历史格式
        let apiHistory = chatMessages.map { ["role": $0.role, "content": $0.content] }

        Task {
            do {
                let response = try await APIService.shared.askQuestion(
                    question: currentQuery,
                    conversationHistory: apiHistory.isEmpty ? nil : apiHistory
                )
                await MainActor.run {
                    // 添加用户消息
                    chatMessages.append(ChatMessage(role: "user", content: currentQuery))
                    // 添加 AI 回答
                    let aiMessage = ChatMessage(
                        role: "assistant",
                        content: response.answer,
                        memoryIds: response.memoryIds ?? []
                    )
                    chatMessages.append(aiMessage)
                    isSearching = false
                }
            } catch {
                await MainActor.run {
                    chatMessages.append(ChatMessage(role: "user", content: currentQuery))
                    chatMessages.append(ChatMessage(role: "assistant", content: "抱歉，AI 思考时遇到了问题。请稍后再试。"))
                    isSearching = false
                }
            }
        }
    }

    private func sendFeedback(for messageId: UUID, wasHelpful: Bool) {
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
        isInputFocused = false
    }
}

// MARK: - 快捷问题按钮
struct QuickQuestionButton: View {
    let question: String
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Text(question)
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "6D6C6A"))
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.white)
            .cornerRadius(20)
            .shadow(color: Color.black.opacity(0.05), radius: 4, y: 2)
        }
    }
}

// MARK: - 聊天气泡
struct ChatBubbleView: View {
    let message: ChatMessage
    let onFeedback: (Bool) -> Void

    var body: some View {
        HStack(alignment: .bottom, spacing: 8) {
            if message.role == "assistant" {
                // AI 头像
                Text("🤖")
                    .font(.system(size: 24))
                    .frame(width: 36, height: 36)
            }

            VStack(alignment: message.role == "user" ? .trailing : .leading, spacing: 6) {
                // 消息气泡
                Text(message.content)
                    .font(.system(size: 15))
                    .foregroundColor(message.role == "user" ? .white : Color(hex: "1A1918"))
                    .lineSpacing(6)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                    .background(message.role == "user" ? Color(hex: "C4935A") : Color.white)
                    .cornerRadius(18)
                    .shadow(color: Color.black.opacity(0.05), radius: 4, y: 2)

                // AI 回答的反馈按钮
                if message.role == "assistant" && !message.memoryIds.isEmpty {
                    feedbackButtons(for: message)
                }
            }

            if message.role == "user" {
                // 用户头像占位
                Spacer()
            }
        }
        .frame(maxWidth: .infinity, alignment: message.role == "user" ? .trailing : .leading)
    }

    @ViewBuilder
    private func feedbackButtons(for message: ChatMessage) -> some View {
        if let feedback = message.feedbackGiven {
            HStack(spacing: 4) {
                Image(systemName: feedback ? "checkmark.circle.fill" : "info.circle.fill")
                    .font(.system(size: 11))
                    .foregroundColor(feedback ? Color(hex: "3D8A5A") : Color(hex: "D08068"))
                Text(feedback ? "感谢反馈" : "已收到")
                    .font(.system(size: 12))
                    .foregroundColor(Color(hex: "9C9B99"))
            }
        } else {
            HStack(spacing: 12) {
                Button {
                    onFeedback(true)
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "hand.thumbsup")
                            .font(.system(size: 12))
                        Text("有帮助")
                            .font(.system(size: 12))
                    }
                    .foregroundColor(Color(hex: "9C9B99"))
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
                    .foregroundColor(Color(hex: "9C9B99"))
                }
            }
        }
    }
}

#Preview {
    SearchView()
}
