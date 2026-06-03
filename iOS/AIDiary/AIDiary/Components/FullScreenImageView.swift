import SwiftUI

/// 全屏图片查看器，支持滑动切换和双击缩放
struct FullScreenImageView: View {
    let imageUrls: [String]
    @Binding var isPresented: Bool
    @State private var currentIndex: Int

    init(imageUrls: [String], selectedIndex: Int, isPresented: Binding<Bool>) {
        self.imageUrls = imageUrls
        self._isPresented = isPresented
        self._currentIndex = State(initialValue: selectedIndex)
    }

    var body: some View {
        ZStack {
            Color.black.ignoresSafeArea()

            TabView(selection: $currentIndex) {
                ForEach(Array(imageUrls.enumerated()), id: \.offset) { index, urlString in
                    ZoomableImageView(urlString: urlString)
                        .tag(index)
                }
            }
            .tabViewStyle(.page(indexDisplayMode: .never))

            // 顶部关闭 + 页码
            VStack {
                HStack {
                    Text("\(currentIndex + 1) / \(imageUrls.count)")
                        .foregroundColor(.white)
                        .font(.subheadline)
                    Spacer()
                    Button(action: { isPresented = false }) {
                        Image(systemName: "xmark.circle.fill")
                            .font(.title)
                            .foregroundColor(.white)
                    }
                }
                .padding(.horizontal, 20)
                .padding(.top, 8)
                Spacer()
            }
        }
    }
}

/// 支持缩放的图片视图
private struct ZoomableImageView: View {
    let urlString: String
    @State private var scale: CGFloat = 1.0
    @State private var lastScale: CGFloat = 1.0
    @State private var offset: CGSize = .zero
    @State private var lastOffset: CGSize = .zero

    var body: some View {
        GeometryReader { geometry in
            AsyncImage(url: URL(string: urlString)) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .scaleEffect(scale)
                        .offset(offset)
                        .gesture(
                            SimultaneousGesture(
                                MagnificationGesture()
                                    .onChanged { value in
                                        scale = lastScale * value
                                    }
                                    .onEnded { _ in
                                        withAnimation {
                                            scale = max(1.0, min(scale, 5.0))
                                        }
                                        lastScale = scale
                                    },
                                TapGesture(count: 2)
                                    .onEnded {
                                        withAnimation {
                                            if scale > 1.0 {
                                                scale = 1.0
                                                lastScale = 1.0
                                                offset = .zero
                                                lastOffset = .zero
                                            } else {
                                                scale = 2.5
                                                lastScale = 2.5
                                            }
                                        }
                                    }
                            )
                        )
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                case .failure:
                    placeholderView
                case .empty:
                    ProgressView().tint(.white)
                @unknown default:
                    placeholderView
                }
            }
        }
    }

    private var placeholderView: some View {
        VStack(spacing: 12) {
            Image(systemName: "photo.badge.exclamationmark")
                .font(.largeTitle)
                .foregroundColor(.gray)
            Text("图片加载失败")
                .foregroundColor(.gray)
        }
    }
}
