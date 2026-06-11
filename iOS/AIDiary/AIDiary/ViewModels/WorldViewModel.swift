//
//  WorldViewModel.swift
//  AIDiary
//
//  虚拟世界视图模型
//

import Foundation
import SwiftUI
import Combine

@MainActor
class WorldViewModel: ObservableObject {
    @Published var characters: [Character] = []
    @Published var relationships: [Relationship] = []
    @Published var locations: [Location] = []
    @Published var stats: WorldStats?
    @Published var isLoading = false
    @Published var errorMessage: String?

    private let layoutPadding: CGFloat = 40

    func loadWorldData() async {
        isLoading = true
        errorMessage = nil

        do {
            // 并行加载人物和关系
            async let charactersTask = APIService.shared.fetchCharacters(limit: 100)
            async let relationshipsTask = APIService.shared.fetchRelationships(minStrength: 0.1, limit: 200)

            self.characters = try await charactersTask
            self.relationships = try await relationshipsTask

            // 布局节点
            layoutNodes()

            isLoading = false

        } catch {
            isLoading = false
            errorMessage = "加载失败: \(error.localizedDescription)"
            print("加载世界数据失败: \(error)")
        }
    }

    func loadStats() async {
        do {
            self.stats = try await APIService.shared.fetchWorldStats()
        } catch {
            print("加载统计信息失败: \(error)")
        }
    }

    /// 简单的圆形布局算法
    private func layoutNodes() {
        guard !characters.isEmpty else { return }

        let centerX: CGFloat = 200  // 画布中心 X
        let centerY: CGFloat = 350  // 画布中心 Y
        let radius: CGFloat = 150   // 圆形半径

        let count = CGFloat(characters.count)

        for (index, character) in characters.enumerated() {
            let angle = (2 * .pi * CGFloat(index)) / count - (.pi / 2)  // 从顶部开始
            let x = centerX + radius * cos(angle)
            let y = centerY + radius * sin(angle)

            if var mutableChar = characters.first(where: { $0.id == character.id }) {
                mutableChar.x = x
                mutableChar.y = y

                if let idx = characters.firstIndex(where: { $0.id == character.id }) {
                    characters[idx] = mutableChar
                }
            }
        }
    }

    /// 获取某个人物的位置
    func getPosition(for characterId: Int) -> CGPoint? {
        guard let character = characters.first(where: { $0.id == characterId }) else {
            return nil
        }
        return CGPoint(x: character.x, y: character.y)
    }

    /// 刷新数据
    func refresh() async {
        await loadWorldData()
    }
}
