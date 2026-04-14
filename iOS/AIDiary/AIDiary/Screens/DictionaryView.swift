import SwiftUI

struct DictionaryView: View {
    @State private var entries: [DictionaryEntry] = []
    @State private var isLoading = false
    @State private var showAddSheet = false
    @State private var newWord = ""
    @State private var editingEntry: DictionaryEntry?
    @State private var editWord = ""
    @State private var showEditSheet = false

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

                    Button {
                        startEdit(entry: entry)
                    } label: {
                        Image(systemName: "pencil")
                            .font(.system(size: 14))
                            .foregroundColor(Color(hex: "8B7EC8"))
                    }
                    .padding(.trailing, 8)

                    Button {
                        deleteEntry(id: entry.id)
                    } label: {
                        Image(systemName: "trash")
                            .font(.system(size: 14))
                            .foregroundColor(Color(hex: "D08068"))
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
                        .background(Color(hex: "8B7EC8"))
                        .cornerRadius(12)
                }
                .disabled(editWord.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(24)
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

    private func deleteEntry(id: Int) {
        Task {
            do {
                try await APIService.shared.deleteDictionaryEntry(id: id)
                await MainActor.run {
                    entries.removeAll { $0.id == id }
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
        guard let entry = editingEntry else { return }
        let word = editWord.trimmingCharacters(in: .whitespaces)
        guard !word.isEmpty else { return }

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
