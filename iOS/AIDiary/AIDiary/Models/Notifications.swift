import Foundation

extension Notification.Name {
    static let diaryDidDelete = Notification.Name("diaryDidDelete")
    static let diaryDidCreate = Notification.Name("diaryDidCreate")
    static let diaryDidUpdate = Notification.Name("diaryDidUpdate")
    static let diaryConfirmSave = Notification.Name("diaryConfirmSave")  // 用户确认保存，关闭录音页面
}