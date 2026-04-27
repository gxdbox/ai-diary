import SwiftUI

struct SearchView: View {
    @State private var query = ""
    @State private var isSearching = false
    @State private var results: [SearchResult] = []
    @State private var showAIAnswer = false
    @State private var aiAnswer = ""
    @State private var currentMemoryIds: [Int] = []
    @State private var feedbackGiven: Bool? = nil  // nil = 未反馈, true = 有帮助, false = 无帮助

    var body: some View {
        VStack(spacing: 0) {
            statusBarPlaceholder
            
            searchBox
            
            if isSearching {
                loadingView
            } else if !aiAnswer.isEmpty {
                aiAnswerView
            } else if results.isEmpty {
                contentSection
            } else {
                resultsList
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
                    results = []
                    aiAnswer = ""
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
    
    private var aiAnswerView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 12) {
                    HStack {
                        Text("🤖")
                            .font(.system(size: 20))
                        Text("AI 回答")
                            .font(.system(size: 16, weight: .semibold))
                            .foregroundColor(Color(hex: "1A1918"))
                    }

                    Text(aiAnswer)
                        .font(.system(size: 15))
                        .foregroundColor(Color(hex: "1A1918"))
                        .lineSpacing(8)
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(Color.white)
                .cornerRadius(16)
                .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)

                // 反馈按钮
                if !currentMemoryIds.isEmpty && feedbackGiven == nil {
                    VStack(spacing: 8) {
                        Text("这个回答对你有帮助吗？")
                            .font(.system(size: 14))
                            .foregroundColor(Color(hex: "6D6C6A"))

                        HStack(spacing: 12) {
                            Button {
                                sendFeedback(wasHelpful: true)
                            } label: {
                                HStack(spacing: 6) {
                                    Image(systemName: "hand.thumbsup.fill")
                                        .font(.system(size: 14))
                                    Text("有帮助")
                                        .font(.system(size: 14))
                                }
                                .foregroundColor(Color(hex: "3D8A5A"))
                                .padding(.horizontal, 16)
                                .padding(.vertical, 10)
                                .background(Color(hex: "C8F0D8"))
                                .cornerRadius(12)
                            }

                            Button {
                                sendFeedback(wasHelpful: false)
                            } label: {
                                HStack(spacing: 6) {
                                    Image(systemName: "hand.thumbsdown.fill")
                                        .font(.system(size: 14))
                                    Text("没帮助")
                                        .font(.system(size: 14))
                                }
                                .foregroundColor(Color(hex: "D08068"))
                                .padding(.horizontal, 16)
                                .padding(.vertical, 10)
                                .background(Color(hex: "F8E0D8"))
                                .cornerRadius(12)
                            }
                        }
                    }
                    .padding(.top, 8)
                }

                // 反馈结果提示
                if let feedback = feedbackGiven {
                    HStack(spacing: 8) {
                        Image(systemName: feedback ? "checkmark.circle.fill" : "info.circle.fill")
                            .font(.system(size: 14))
                            .foregroundColor(feedback ? Color(hex: "3D8A5A") : Color(hex: "D08068"))
                        Text(feedback ? "感谢反馈，我会继续改进！" : "收到，下次我会尝试更好的回答")
                            .font(.system(size: 14))
                            .foregroundColor(Color(hex: "6D6C6A"))
                    }
                    .padding(.top, 8)
                }

                Button {
                    aiAnswer = ""
                    results = []
                    query = ""
                    currentMemoryIds = []
                    feedbackGiven = nil
                } label: {
                    Text("再问一次")
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "C4935A"))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color(hex: "C4935A").opacity(0.1))
                        .cornerRadius(12)
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 100)
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
    
    private var resultsList: some View {
        ScrollView {
            LazyVStack(spacing: 12) {
                ForEach(results) { result in
                    SearchResultCard(result: result)
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 100)
        }
    }
    
    private func askAI() {
        guard !query.isEmpty else { return }
        isSearching = true
        aiAnswer = ""
        currentMemoryIds = []
        feedbackGiven = nil
        Task {
            do {
                let response = try await APIService.shared.askQuestion(question: query)
                await MainActor.run {
                    aiAnswer = response.answer
                    currentMemoryIds = response.memoryIds ?? []
                    isSearching = false
                }
            } catch {
                await MainActor.run {
                    aiAnswer = "抱歉，AI 思考时遇到了问题。请稍后再试。"
                    isSearching = false
                }
            }
        }
    }

    private func sendFeedback(wasHelpful: Bool) {
        guard !currentMemoryIds.isEmpty else { return }
        Task {
            do {
                try await APIService.shared.sendFeedback(memoryIds: currentMemoryIds, wasHelpful: wasHelpful)
                await MainActor.run {
                    feedbackGiven = wasHelpful
                }
            } catch {
                // 反馈失败不影响用户体验，静默处理
                await MainActor.run {
                    feedbackGiven = wasHelpful
                }
            }
        }
    }
    
    private func performSearch() {
        guard !query.isEmpty else { return }
        isSearching = true
        Task {
            do {
                let response = try await APIService.shared.semanticSearch(query: query)
                await MainActor.run {
                    results = response.results
                    isSearching = false
                }
            } catch {
                await MainActor.run {
                    isSearching = false
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

struct SearchResultCard: View {
    let result: SearchResult
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(result.text)
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "1A1918"))
                .lineLimit(3)
            
            Text("相关度: \(Int(result.score * 100))%")
                .font(.system(size: 12))
                .foregroundColor(Color(hex: "9C9B99"))
        }
        .padding(16)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color.white)
        .cornerRadius(12)
        .shadow(color: Color.black.opacity(0.08), radius: 8, y: 2)
    }
}

#Preview {
    ContentView()
}