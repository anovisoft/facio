import Foundation

enum DisplayCopy {
    static func title(subjectId: String, stored: String) -> String {
        switch subjectId {
        case "push-ups": String(localized: "Отжимания", comment: "Subject title for push-ups")
        case "vegetables": String(localized: "Овощи", comment: "Subject title for vegetables")
        case "bike": String(localized: "Велосипед", comment: "Subject title for the exercise bike")
        default: stored
        }
    }
}
