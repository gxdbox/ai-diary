import Foundation

/// 金句/名言数据集
struct Quote {
    let text: String
    let author: String
    let category: QuoteCategory?
}

enum QuoteCategory {
    case life      // 生活
    case growth    // 成长
    case emotion   // 情绪
    case time      // 时间
    case journal   // 日记相关
}

/// 金句库
struct QuoteLibrary {
    static let quotes: [Quote] = [
        // 生活感悟
        Quote(text: "生活不是等待暴风雨过去，而是学会在雨中跳舞。", author: "维维安·格林", category: .life),
        Quote(text: "每一个不曾起舞的日子，都是对生命的辜负。", author: "尼采", category: .life),
        Quote(text: "生活就像一面镜子，你对它笑，它就对你笑。", author: "林肯", category: .life),
        Quote(text: "世界上只有一种真正的英雄主义，那就是认清生活的真相后依然热爱生活。", author: "罗曼·罗兰", category: .life),
        Quote(text: "生活不可能像你想象得那么好，但也不会像你想象得那么糟。", author: "莫泊桑", category: .life),
        Quote(text: "人生没有彩排，每一天都是现场直播。", author: "佚名", category: .life),
        Quote(text: "把每一天当作生命的最后一天去过，你就会活得从容。", author: "佚名", category: .life),
        Quote(text: "生活中最重要的事情不是你所处的位置，而是你前进的方向。", author: "奥利弗·温德尔·霍姆斯", category: .life),

        // 成长励志
        Quote(text: "不要因为走得太远，而忘记为什么出发。", author: "纪伯伦", category: .growth),
        Quote(text: "成长就是不断与自己和解的过程。", author: "佚名", category: .growth),
        Quote(text: "你若盛开，清风自来。", author: "佚名", category: .growth),
        Quote(text: "每一次努力，都是幸运的伏笔。", author: "佚名", category: .growth),
        Quote(text: "成为更好的自己，是人生最大的成功。", author: "佚名", category: .growth),
        Quote(text: "你今天的努力，是幸运的伏笔；当下的付出，是明日的花开。", author: "佚名", category: .growth),
        Quote(text: "无论你走到哪里，无论天气多么坏，记得带上你自己的阳光。", author: "佚名", category: .growth),
        Quote(text: "人生最大的勇敢，是经历欺骗和伤害之后，还能保持信任和爱的能力。", author: "佚名", category: .growth),

        // 情绪调节
        Quote(text: "情绪不是你的敌人，它是你内心的信使。", author: "佚名", category: .emotion),
        Quote(text: "允许自己不开心，也是一种开心。", author: "佚名", category: .emotion),
        Quote(text: "与其生气，不如争气；与其抱怨，不如改变。", author: "佚名", category: .emotion),
        Quote(text: "心若向阳，无谓悲伤。", author: "佚名", category: .emotion),
        Quote(text: "快乐不是因为拥有的多，而是计较的少。", author: "佚名", category: .emotion),
        Quote(text: "真正的平静，不是避开车马喧嚣，而是在心中修篱种菊。", author: "白落梅", category: .emotion),
        Quote(text: "焦虑不会消除明天的悲伤，它只会消耗今天的力量。", author: "佚名", category: .emotion),

        // 时间珍惜
        Quote(text: "时间是最公平的，给每个人都是24小时；时间也是最偏心的，给每个人都不是24小时。", author: "佚名", category: .time),
        Quote(text: "一寸光阴一寸金，寸金难买寸光阴。", author: "谚语", category: .time),
        Quote(text: "时间就像海绵里的水，只要愿挤，总还是有的。", author: "鲁迅", category: .time),
        Quote(text: "珍惜今天，珍惜现在，谁知道明天和意外，哪一个先来。", author: "佚名", category: .time),
        Quote(text: "过去已成历史，未来尚不可知，现在才是礼物。", author: "佚名", category: .time),

        // 日记相关
        Quote(text: "写日记是与自己对话的过程，它能帮助你更清晰地认识自己。", author: "佚名", category: .journal),
        Quote(text: "日记是时光的容器，记录着我们的喜怒哀乐。", author: "佚名", category: .journal),
        Quote(text: "每一个平凡的日子，都值得被记录。", author: "佚名", category: .journal),
        Quote(text: "记录生活，是为了更好地生活。", author: "佚名", category: .journal),
        Quote(text: "文字能留住记忆，让瞬间成为永恒。", author: "佚名", category: .journal),
        Quote(text: "日记是通往内心的桥梁。", author: "佚名", category: .journal),
        Quote(text: "用文字记录心情，让回忆有迹可循。", author: "佚名", category: .journal),
        Quote(text: "每一天都是限量版，值得用心记录。", author: "佚名", category: .journal),
    ]

    /// 随机获取一条金句
    static func randomQuote() -> Quote {
        quotes.randomElement() ?? quotes[0]
    }

    /// 根据类别随机获取金句
    static func randomQuote(category: QuoteCategory) -> Quote {
        let filtered = quotes.filter { $0.category == category }
        return filtered.randomElement() ?? randomQuote()
    }
}