// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "nyx-semantic",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "nyx-semantic", targets: ["NyxSemantic"]),
    ],
    targets: [
        .executableTarget(
            name: "NyxSemantic",
            path: "Sources/NyxSemantic"
        ),
    ]
)
