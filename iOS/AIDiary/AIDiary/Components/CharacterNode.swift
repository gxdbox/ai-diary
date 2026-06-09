//
//  CharacterNode.swift
//  AIDiary
//
//  人物节点组件
//

import SwiftUI

struct CharacterNode: View {
    let character: Character
    @GestureState private var isDragging = false
    var onTap: (() -> Void)? = nil

    var body: some View {
        VStack(spacing: 4) {
            // 人物头像圆圈
            Circle()
                .fill(Color(hex: character.avatarColor))
                .frame(width: 60, height: 60)
                .overlay(
                    Text(String(character.name.prefix(1)))
                        .font(.system(size: 24, weight: .bold))
                        .foregroundColor(.white)
                )
                .shadow(color: Color.black.opacity(0.2), radius: 4, x: 0, y: 2)
                .scaleEffect(isDragging ? 1.1 : 1.0)
                .animation(.easeInOut(duration: 0.2), value: isDragging)

            // 人物名称
            Text(character.name)
                .font(.caption)
                .fontWeight(.medium)
                .lineLimit(1)
                .frame(maxWidth: 80)

            // 出现次数徽章
            Text("\(character.appearanceCount)")
                .font(.caption2)
                .foregroundColor(.secondary)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Color.gray.opacity(0.15))
                .cornerRadius(8)
        }
        .gesture(
            DragGesture()
                .updating($isDragging) { _, state, _ in
                    state = true
                }
        )
        .onTapGesture {
            onTap?()
        }
        .accessibilityLabel("人物: \(character.name)，出现\(character.appearanceCount)次")
    }
}

// MARK: - Preview
struct CharacterNode_Previews: PreviewProvider {
    static var previews: some View {
        ZStack {
            Color.gray.opacity(0.1)

            CharacterNode(
                character: Character(
                    id: 1,
                    name: "张三",
                    appearanceCount: 15,
                    avatarColor: "#4A90E2",
                    firstAppearance: Date(),
                    lastAppearance: Date()
                )
            )
        }
        .frame(width: 200, height: 200)
    }
}
