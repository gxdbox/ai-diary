import SwiftUI

/// 图片缩略图网格组件
/// 1 张全宽，2 张并排，3 张 2+1 布局
struct ImageGridView: View {
    let imageUrls: [String]
    let isEditing: Bool
    let onDelete: ((Int) -> Void)?
    let onTapImage: ((Int) -> Void)?

    init(imageUrls: [String],
         isEditing: Bool = false,
         onDelete: ((Int) -> Void)? = nil,
         onTapImage: ((Int) -> Void)? = nil) {
        self.imageUrls = imageUrls
        self.isEditing = isEditing
        self.onDelete = onDelete
        self.onTapImage = onTapImage
    }

    var body: some View {
        if imageUrls.isEmpty { return AnyView(EmptyView()) }

        return AnyView(
            VStack(spacing: 8) {
                if imageUrls.count == 1 {
                    imageCell(index: 0)
                        .frame(height: 200)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                } else if imageUrls.count == 2 {
                    HStack(spacing: 8) {
                        imageCell(index: 0)
                        imageCell(index: 1)
                    }
                    .frame(height: 160)
                } else {
                    // 3 张：上排 2 + 下排 1
                    HStack(spacing: 8) {
                        imageCell(index: 0)
                        imageCell(index: 1)
                    }
                    .frame(height: 140)
                    imageCell(index: 2)
                        .frame(height: 200)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                }
            }
        )
    }

    @ViewBuilder
    private func imageCell(index: Int) -> some View {
        let urlString = imageUrls[index]
        ZStack(alignment: .topTrailing) {
            AsyncImage(url: URL(string: urlString)) { phase in
                switch phase {
                case .success(let image):
                    image
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                case .failure:
                    placeholderView
                case .empty:
                    ProgressView()
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                        .background(Color(.systemGray6))
                @unknown default:
                    placeholderView
                }
            }
            .clipped()
            .onTapGesture {
                onTapImage?(index)
            }

            // 删除按钮
            if isEditing, let onDelete = onDelete {
                Button(action: { onDelete(index) }) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title3)
                        .foregroundColor(.white)
                        .shadow(radius: 2)
                        .padding(6)
                }
            }
        }
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private var placeholderView: some View {
        ZStack {
            Color(.systemGray5)
            Image(systemName: "photo.badge.exclamationmark")
                .font(.title2)
                .foregroundColor(.gray)
        }
    }
}
