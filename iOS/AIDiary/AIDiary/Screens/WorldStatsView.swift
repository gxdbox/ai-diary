//
//  WorldStatsView.swift
//  AIDiary
//
//  虚拟世界统计面板
//

import SwiftUI

struct WorldStatsView: View {
    let stats: WorldStats?
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationView {
            List {
                // 世界概览
                Section("世界概览") {
                    StatRow(title: "人物总数", value: "\(stats?.totalCharacters ?? 0)")
                    StatRow(title: "关系总数", value: "\(stats?.totalRelationships ?? 0)")
                    StatRow(title: "地点总数", value: "\(stats?.totalLocations ?? 0)")
                }

                // 最活跃人物
                if let mostActive = stats?.mostActiveCharacter {
                    Section("最活跃人物") {
                        HStack {
                            Circle()
                                .fill(Color(hex: mostActive.avatarColor))
                                .frame(width: 40, height: 40)
                                .overlay(
                                    Text(String(mostActive.name.prefix(1)))
                                        .font(.headline)
                                        .foregroundColor(.white)
                                )

                            VStack(alignment: .leading, spacing: 4) {
                                Text(mostActive.name)
                                    .font(.body)
                                    .fontWeight(.medium)
                                Text("出现 \(mostActive.appearanceCount) 次")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }

                            Spacer()
                        }
                        .padding(.vertical, 4)
                    }
                }

                // 最强关系
                if let strongest = stats?.strongestRelationship {
                    Section("最强关系") {
                        HStack {
                            Text(strongest.characterAName ?? "?")
                                .font(.body)
                                .fontWeight(.medium)

                            Image(systemName: "arrow.left.arrow.right")
                                .foregroundColor(.blue)

                            Text(strongest.characterBName ?? "?")
                                .font(.body)
                                .fontWeight(.medium)

                            Spacer()

                            Text("\(Int(strongest.strength * 100))%")
                                .font(.caption)
                                .foregroundColor(.secondary)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.blue.opacity(0.1))
                                .cornerRadius(8)
                        }
                        .padding(.vertical, 4)

                        Text("关系类型: \(strongest.relationshipType)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }

                // 说明
                Section {
                    Text("统计数据基于你的日记内容自动生成\n人物和关系会随着新日记的添加而更新")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .navigationTitle("世界统计")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("关闭") {
                        dismiss()
                    }
                }
            }
        }
    }
}

// MARK: - 统计行组件
struct StatRow: View {
    let title: String
    let value: String

    var body: some View {
        HStack {
            Text(title)
                .font(.body)
            Spacer()
            Text(value)
                .font(.body)
                .fontWeight(.semibold)
                .foregroundColor(.blue)
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Preview
struct WorldStatsView_Previews: PreviewProvider {
    static var previews: some View {
        WorldStatsView(stats: nil)
    }
}
