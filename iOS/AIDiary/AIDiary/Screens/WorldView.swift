//
//  WorldView.swift
//  AIDiary
//
//  虚拟世界主视图 - 2D 知识图谱可视化
//

import SwiftUI

struct WorldView: View {
    @StateObject private var viewModel = WorldViewModel()
    @State private var selectedCharacter: Character?
    @State private var showStats = false

    var body: some View {
        ZStack {
            // 背景网格
            GridBackground()

            if viewModel.isLoading {
                // 加载状态
                VStack(spacing: 16) {
                    ProgressView()
                        .scaleEffect(1.5)
                    Text("加载虚拟世界...")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

            } else if let errorMessage = viewModel.errorMessage {
                // 错误状态
                VStack(spacing: 16) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.system(size: 48))
                        .foregroundColor(.orange)
                    Text(errorMessage)
                        .font(.body)
                        .multilineTextAlignment(.center)
                        .padding()
                    Button("重试") {
                        Task {
                            await viewModel.loadWorldData()
                        }
                    }
                    .buttonStyle(.borderedProminent)
                }

            } else if viewModel.characters.isEmpty {
                // 空状态
                EmptyWorldView(onRefresh: {
                    Task {
                        await viewModel.loadWorldData()
                    }
                })

            } else {
                // 图谱内容
                ZStack {
                    // 关系连线（在底层）
                    Canvas { context, size in
                        drawRelationships(context: context, size: size)
                    }

                    // 人物节点
                    ForEach(viewModel.characters) { character in
                        CharacterNode(character: character) {
                            selectedCharacter = character
                        }
                        .position(x: character.x, y: character.y)
                    }

                    // 顶部工具栏
                    VStack {
                        HStack {
                            Spacer()

                            Button(action: { showStats = true }) {
                                Image(systemName: "chart.bar.fill")
                                    .font(.title3)
                                    .padding(10)
                                    .background(Color.white.opacity(0.9))
                                    .clipShape(Circle())
                                    .shadow(radius: 2)
                            }

                            Button(action: {
                                Task {
                                    await viewModel.refresh()
                                }
                            }) {
                                Image(systemName: "arrow.clockwise")
                                    .font(.title3)
                                    .padding(10)
                                    .background(Color.white.opacity(0.9))
                                    .clipShape(Circle())
                                    .shadow(radius: 2)
                            }
                        }
                        .padding()

                        Spacer()
                    }
                }
            }
        }
        .navigationTitle("虚拟世界")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(item: $selectedCharacter) { character in
            CharacterDetailView(character: character)
        }
        .sheet(isPresented: $showStats) {
            WorldStatsView(stats: viewModel.stats)
        }
        .onAppear {
            Task {
                await viewModel.loadWorldData()
                await viewModel.loadStats()
            }
        }
        .refreshable {
            await viewModel.refresh()
        }
    }

    /// 绘制关系连线
    private func drawRelationships(context: GraphicsContext, size: CGSize) {
        for relationship in viewModel.relationships {
            guard let posA = viewModel.getPosition(for: relationship.characterAId),
                  let posB = viewModel.getPosition(for: relationship.characterBId) else {
                continue
            }

            // 根据关系强度设置线条粗细和透明度
            let lineWidth = CGFloat(relationship.strength) * 4 + 1
            let opacity = CGFloat(relationship.strength) * 0.6 + 0.2

            let path = Path { p in
                p.move(to: posA)
                p.addLine(to: posB)
            }

            context.stroke(
                path,
                with: .color(Color.blue.opacity(opacity)),
                lineWidth: lineWidth
            )
        }
    }
}

// MARK: - 背景网格
struct GridBackground: View {
    var body: some View {
        GeometryReader { geometry in
            Canvas { context, size in
                let gridSize: CGFloat = 40
                let color = Color.gray.opacity(0.1)

                // 垂直线
                for x in stride(from: 0, through: size.width, by: gridSize) {
                    context.stroke(
                        Path { $0.move(to: CGPoint(x: x, y: 0)); $0.addLine(to: CGPoint(x: x, y: size.height)) },
                        with: .color(color),
                        lineWidth: 0.5
                    )
                }

                // 水平线
                for y in stride(from: 0, through: size.height, by: gridSize) {
                    context.stroke(
                        Path { $0.move(to: CGPoint(x: 0, y: y)); $0.addLine(to: CGPoint(x: size.width, y: y)) },
                        with: .color(color),
                        lineWidth: 0.5
                    )
                }
            }
        }
        .ignoresSafeArea()
    }
}

// MARK: - 空状态视图
struct EmptyWorldView: View {
    let onRefresh: () -> Void

    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "globe.americas.fill")
                .font(.system(size: 64))
                .foregroundColor(.gray.opacity(0.4))

            Text("虚拟世界尚未生成")
                .font(.title2)
                .fontWeight(.semibold)

            Text("开始记录日记，AI 会自动提取\n你日记中的人物和关系")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button(action: onRefresh) {
                Label("刷新", systemImage: "arrow.clockwise")
                    .font(.body)
                    .padding(.horizontal, 24)
                    .padding(.vertical, 12)
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
            }
        }
        .padding()
    }
}

// MARK: - Preview
struct WorldView_Previews: PreviewProvider {
    static var previews: some View {
        NavigationView {
            WorldView()
        }
    }
}
