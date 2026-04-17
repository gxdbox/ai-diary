import SwiftUI

struct DictionaryView: View {
    @State private var entries: [DictionaryEntry] = []
    @State private var isLoading = false
    @State private var showAddSheet = false
    @State private var newWord = ""
    @State private var editingEntry: DictionaryEntry?
    @State private var editWord = ""
    @State private var showEditSheet = false
    @State private var deletingEntryId: Int?
    @State private var showDeleteConfirm = false
    @FocusState private var isEditFieldFocused: Bool

    // 判断编辑内容是否有改动
    private var hasEditChange: Bool {
        guard let entry = editingEntry else { return false }
        let trimmedEditWord = editWord.trimmingCharacters(in: .whitespaces)
        return !trimmedEditWord.isEmpty && trimmedEditWord != entry.word
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                statusBarPlaceholder

                titleSection

                addWordSection

                if isLoading {
                    loadingView
                } else if entries.isEmpty {
                    emptyView
                } else {
                    entriesList
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 100)
        }
        .background(Color(hex: "F5F4F1"))
        .onAppear {
            loadEntries()
        }
        .alert("确定删除这个词汇吗？", isPresented: $showDeleteConfirm) {
            Button("删除", role: .destructive) {
                if let entryId = deletingEntryId {
                    performDelete(id: entryId)
                }
            }
            Button("取消", role: .cancel) {
                deletingEntryId = nil
            }
        } message: {
            if let entry = entries.first(where: { $0.id == deletingEntryId }) {
                Text("「\(entry.word)」将被删除")
            } else {
                Text("此操作不可撤销")
            }
        }
    }

    private var statusBarPlaceholder: some View {
        Color.clear.frame(height: 62)
    }

    private var titleSection: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("自定义词典")
                .font(.system(size: 26, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))

            Text("添加专业词汇或人名，语音转文字时自动校正同音词")
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "9C9B99"))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var addWordSection: some View {
        HStack(spacing: 12) {
            TextField("输入词汇，如：桐桐、Claude Code", text: $newWord)
                .font(.system(size: 15))
                .padding(12)
                .background(Color.white)
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color(hex: "E5E4E1"), lineWidth: 1)
                )

            Button {
                addWord()
            } label: {
                Text("添加")
                    .font(.system(size: 14, weight: .medium))
                    .foregroundColor(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                    .background(Color(hex: "8B7EC8"))
                    .cornerRadius(12)
            }
            .disabled(newWord.trimmingCharacters(in: .whitespaces).isEmpty)
        }
    }

    private var loadingView: some View {
        VStack {
            Spacer()
            ProgressView()
                .tint(Color(hex: "8B7EC8"))
            Spacer()
        }
    }

    private var emptyView: some View {
        VStack(spacing: 16) {
            Spacer()
            Text("📖")
                .font(.system(size: 48))
            Text("还没有添加词汇")
                .font(.system(size: 16, weight: .semibold))
                .foregroundColor(Color(hex: "1A1918"))
            Text("添加常用词汇，语音转文字时自动校正")
                .font(.system(size: 14))
                .foregroundColor(Color(hex: "9C9B99"))
            Spacer()
        }
    }

    private var entriesList: some View {
        VStack(spacing: 12) {
            ForEach(entries, id: \.id) { entry in
                HStack {
                    Text(entry.word)
                        .font(.system(size: 16, weight: .medium))
                        .foregroundColor(Color(hex: "1A1918"))

                    Spacer()

                    // 编辑按钮
                    Button {
                        startEdit(entry: entry)
                    } label: {
                        Text("编辑")
                            .font(.system(size: 13))
                            .foregroundColor(Color(hex: "8B7EC8"))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(Color(hex: "8B7EC8").opacity(0.1))
                            .cornerRadius(8)
                    }

                    // 删除按钮（加大间距）
                    Button {
                        deletingEntryId = entry.id
                        showDeleteConfirm = true
                    } label: {
                        Text("删除")
                            .font(.system(size: 13))
                            .foregroundColor(Color(hex: "D08068"))
                            .padding(.horizontal, 12)
                            .padding(.vertical, 6)
                            .background(Color(hex: "D08068").opacity(0.1))
                            .cornerRadius(8)
                    }
                }
                .padding(16)
                .background(Color.white)
                .cornerRadius(12)
                .shadow(color: Color.black.opacity(0.05), radius: 8, y: 2)
            }
        }
        .sheet(isPresented: $showEditSheet) {
            editSheet
        }
    }

    private var editSheet: some View {
        VStack(spacing: 24) {
            Text("编辑词汇")
                .font(.system(size: 20, weight: .semibold))

            TextField("输入词汇", text: $editWord)
                .font(.system(size: 15))
                .padding(12)
                .background(Color(hex: "F5F4F1"))
                .cornerRadius(12)
                .focused($isEditFieldFocused)

            HStack(spacing: 16) {
                Button {
                    showEditSheet = false
                } label: {
                    Text("取消")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(Color(hex: "1A1918"))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(Color(hex: "E5E4E1"))
                        .cornerRadius(12)
                }

                Button {
                    saveEdit()
                } label: {
                    Text("保存")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 12)
                        .background(hasEditChange ? Color(hex: "8B7EC8") : Color(hex: "C8C7C5"))
                        .cornerRadius(12)
                }
            }
        }
        .padding(24)
        .onAppear {
            // 确保 Sheet 显示时 editWord 正确初始化
            if let entry = editingEntry, editWord.isEmpty {
                editWord = entry.word
            }
            // 自动聚焦 TextField，用户可直接输入
            isEditFieldFocused = true
        }
    }

    private func loadEntries() {
        isLoading = true
        Task {
            do {
                let response = try await APIService.shared.fetchDictionary()
                await MainActor.run {
                    entries = response.entries
                    isLoading = false
                }
            } catch {
                await MainActor.run {
                    isLoading = false
                    print("加载词典失败：\(error)")
                }
            }
        }
    }

    private func addWord() {
        let word = newWord.trimmingCharacters(in: .whitespaces)
        guard !word.isEmpty else { return }

        Task {
            do {
                let entry = try await APIService.shared.addDictionaryEntry(word: word)
                await MainActor.run {
                    entries.insert(entry, at: 0)
                    newWord = ""
                }
            } catch {
                print("添加失败：\(error)")
            }
        }
    }

    private func performDelete(id: Int) {
        Task {
            do {
                try await APIService.shared.deleteDictionaryEntry(id: id)
                await MainActor.run {
                    entries.removeAll { $0.id == id }
                    deletingEntryId = nil
                }
            } catch {
                print("删除失败：\(error)")
            }
        }
    }

    private func startEdit(entry: DictionaryEntry) {
        editingEntry = entry
        editWord = entry.word
        showEditSheet = true
    }

    private func saveEdit() {
        // 无论是否有改动，点击保存都关闭 sheet
        let word = editWord.trimmingCharacters(in: .whitespaces)
        guard let entry = editingEntry, !word.isEmpty, word != entry.word else {
            // 无改动或空内容，直接关闭
            showEditSheet = false
            editingEntry = nil
            return
        }

        // 有修改，调用 API 更新
        Task {
            do {
                let updated = try await APIService.shared.updateDictionaryEntry(id: entry.id, word: word)
                await MainActor.run {
                    if let index = entries.firstIndex(where: { $0.id == entry.id }) {
                        entries[index] = updated
                    }
                    showEditSheet = false
                    editingEntry = nil
                }
            } catch {
                print("更新失败：\(error)")
            }
        }
    }
}

#Preview {
    DictionaryView()
}
