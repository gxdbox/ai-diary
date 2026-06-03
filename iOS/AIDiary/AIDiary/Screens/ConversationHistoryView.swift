import SwiftUI

struct ConversationHistoryView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var conversations: [CachedConversation] = []
    @State private var isLoading = true

    let onSelectConversation: (CachedConversation) -> Void

    var body: some View {
        NavigationView {
            Group {
                if isLoading {
                    ProgressView("加载中...")
                } else if conversations.isEmpty {
                    VStack(spacing: 16) {
                        Text("📝")
                            .font(.system(size: 48))
                        Text("暂无历史对话")
                            .font(.system(size: 16))
                            .foregroundColor(Color(hex: "9C9B99"))
                    }
                } else {
                    List {
                        ForEach(conversations, id: \.id) { conversation in
                            Button {
                                onSelectConversation(conversation)
                                dismiss()
                            } label: {
                                VStack(alignment: .leading, spacing: 6) {
                                    Text(conversation.title)
                                        .font(.system(size: 15, weight: .medium))
                                        .foregroundColor(Color(hex: "1A1918"))
                                        .lineLimit(1)

                                    Text(formatDate(conversation.updatedAt))
                                        .font(.system(size: 12))
                                        .foregroundColor(Color(hex: "9C9B99"))

                                    Text("\(conversation.messages.count) 条消息")
                                        .font(.system(size: 12))
                                        .foregroundColor(Color(hex: "C4C4C4"))
                                }
                                .padding(.vertical, 4)
                            }
                            .swipeActions(edge: .trailing, allowsFullSwipe: true) {
                                deleteButton(for: conversation)
                            }
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("历史对话")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("关闭") {
                        dismiss()
                    }
                    .foregroundColor(Color(hex: "C4935A"))
                }
            }
        }
        .task {
            await loadConversations()
        }
    }

    private func deleteButton(for conversation: CachedConversation) -> some View {
        Button(role: .destructive) {
            Task {
                await CacheService.shared.deleteConversation(id: conversation.id)
                await loadConversations()
            }
        } label: {
            Image(systemName: "trash")
        }
    }

    private func loadConversations() async {
        conversations = await CacheService.shared.getAllConversations()
        isLoading = false
    }

    private func formatDate(_ date: Date) -> String {
        let formatter = DateFormatter()
        let calendar = Calendar.current

        if calendar.isDateInToday(date) {
            formatter.dateFormat = "今天 HH:mm"
        } else if calendar.isDateInYesterday(date) {
            formatter.dateFormat = "昨天 HH:mm"
        } else {
            formatter.dateFormat = "MM-dd HH:mm"
        }
        return formatter.string(from: date)
    }
}
