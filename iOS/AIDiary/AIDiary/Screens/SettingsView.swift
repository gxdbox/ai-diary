import SwiftUI

struct SettingsView: View {
    @State private var autoCleanText = true
    @State private var localEncryption = true
    @State private var faceIDEnabled = false
    @State private var showDictionary = false

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                statusBarPlaceholder

                titleSection

                userCard

                recordingSettingsCard

                aiSettingsCard

                privacyCard

                otherCard

                logoutButton
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 100)
        }
        .background(Color(hex: "F5F4F1"))
        .sheet(isPresented: $showDictionary) {
            DictionaryView()
        }
    }

    private var statusBarPlaceholder: some View {
        Color.clear.frame(height: 62)
    }

    private var titleSection: some View {
        Text("设置")
            .font(.system(size: 26, weight: .semibold))
            .foregroundColor(Color(hex: "1A1918"))
            .frame(maxWidth: .infinity, alignment: .leading)
    }

    private var userCard: some View {
        HStack(spacing: 16) {
            // 头像
            Circle()
                .fill(Color(hex: "C4935A"))
                .frame(width: 56, height: 56)
                .overlay(
                    Text("我")
                        .font(.system(size: 20, weight: .medium))
                        .foregroundColor(.white)
                )

            // 用户信息
            VStack(alignment: .leading, spacing: 4) {
                Text("松果收藏家")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundColor(Color(hex: "1A1918"))

                Text("珍藏每一颗记忆")
                    .font(.system(size: 13))
                    .foregroundColor(Color(hex: "6D6C6A"))
            }

            Spacer()
        }
        .padding(16)
        .background(Color.white)
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)
    }

    private var recordingSettingsCard: some View {
        VStack(alignment: .leading, spacing: 0) {
            sectionTitle("录音设置")

            settingItem("语音识别语言", value: "中文", showArrow: true)
            divider()
            settingToggle("自动清洗文本", isOn: $autoCleanText)
            divider()
            settingItem("录音质量", value: "标准", showArrow: true)
            divider()
            Button {
                showDictionary = true
            } label: {
                HStack {
                    Text("自定义词典")
                        .font(.system(size: 15))
                        .foregroundColor(Color(hex: "1A1918"))
                    Spacer()
                    Image(systemName: "chevron.right")
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "9C9B99"))
                }
                .padding(.vertical, 14)
                .padding(.horizontal, 16)
            }
        }
        .padding(16)
        .background(Color.white)
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)
    }

    private var aiSettingsCard: some View {
        VStack(alignment: .leading, spacing: 0) {
            sectionTitle("AI设置")

            settingItem("AI服务提供商", value: "阿里云百炼", showArrow: false)
        }
        .padding(16)
        .background(Color.white)
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)
    }

    private var privacyCard: some View {
        VStack(alignment: .leading, spacing: 0) {
            sectionTitle("隐私与安全")

            settingToggle("本地数据加密", isOn: $localEncryption)
            divider()
            settingToggle("面容ID锁定", isOn: $faceIDEnabled)
        }
        .padding(16)
        .background(Color.white)
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)
    }

    private var otherCard: some View {
        VStack(alignment: .leading, spacing: 0) {
            sectionTitle("其他")

            HStack {
                Text("主题颜色")
                    .font(.system(size: 15))
                    .foregroundColor(Color(hex: "1A1918"))
                Spacer()
                Circle()
                    .fill(Color(hex: "C4935A"))
                    .frame(width: 20, height: 20)
            }
            .padding(.vertical, 14)
            .padding(.horizontal, 16)

            divider()

            HStack {
                Text("关于我们")
                    .font(.system(size: 15))
                    .foregroundColor(Color(hex: "1A1918"))
                Spacer()
                Image(systemName: "chevron.right")
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "9C9B99"))
            }
            .padding(.vertical, 14)
            .padding(.horizontal, 16)
        }
        .padding(16)
        .background(Color.white)
        .cornerRadius(16)
        .shadow(color: Color.black.opacity(0.08), radius: 12, y: 2)
    }

    private var logoutButton: some View {
        Button {
            // 退出登录操作
        } label: {
            Text("退出登录")
                .font(.system(size: 15))
                .foregroundColor(Color(hex: "D08068"))
                .frame(maxWidth: .infinity)
                .frame(height: 48)
                .background(Color.white)
                .cornerRadius(12)
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(Color(hex: "D08068"), lineWidth: 1)
                )
        }
    }

    private func sectionTitle(_ text: String) -> some View {
        Text(text)
            .font(.system(size: 12))
            .foregroundColor(Color(hex: "9C9B99"))
            .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func settingItem(_ title: String, value: String, showArrow: Bool) -> some View {
        HStack {
            Text(title)
                .font(.system(size: 15))
                .foregroundColor(Color(hex: "1A1918"))
            Spacer()
            HStack(spacing: 4) {
                Text(value)
                    .font(.system(size: 14))
                    .foregroundColor(Color(hex: "6D6C6A"))
                if showArrow {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 14))
                        .foregroundColor(Color(hex: "9C9B99"))
                }
            }
        }
        .padding(.vertical, 14)
        .padding(.horizontal, 16)
    }

    private func settingToggle(_ title: String, isOn: Binding<Bool>) -> some View {
        HStack {
            Text(title)
                .font(.system(size: 15))
                .foregroundColor(Color(hex: "1A1918"))
            Spacer()
            Toggle("", isOn: isOn)
                .labelsHidden()
                .tint(Color(hex: "C4935A"))
        }
        .padding(.vertical, 14)
        .padding(.horizontal, 16)
    }

    private func divider() -> some View {
        Rectangle()
            .fill(Color(hex: "E5E4E1"))
            .frame(height: 1)
    }
}

#Preview {
    SettingsView()
}