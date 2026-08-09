import Foundation

// Yerdchi = Nyx semantic understanding + BUbiNG-style crawl scheduling.
// It is intentionally dependency-free so the core remains local, deterministic,
// auditable, and usable from the existing Swift executable target.

struct YerdchiConfiguration {
    var maxPages: Int = 1_000
    var maxDepth: Int = 4
    var maxRetries: Int = 3
    var perHostConcurrency: Int = 2
    var minimumHostDelay: TimeInterval = 0.35
    var leaseDuration: TimeInterval = 30
    var semanticIntent: String = ""
    var allowedHosts: Set<String> = []
}

enum YerdchiJobState: String, Codable {
    case queued
    case leased
    case succeeded
    case failed
    case blocked
}

struct YerdchiURLJob: Codable {
    let id: UUID
    let url: URL
    let canonicalURL: String
    let host: String
    let depth: Int
    let parentURL: String?
    let discoveredAt: Date
    var nextEligibleAt: Date
    var leaseExpiresAt: Date?
    var attempts: Int
    var priority: Double
    var state: YerdchiJobState
    var lastError: String?
}

struct YerdchiObservation: Codable {
    let url: String
    let title: String
    let contentHash: String
    let semanticHash: String
    let discoveredLinks: [String]
    let semanticMatches: [YerdchiSemanticMatch]
    let observedAt: Date
    let elapsedMilliseconds: Int
}

struct YerdchiSemanticMatch: Codable {
    let rank: Int
    let score: Double
    let tag: String
    let text: String
    let xpath: String
}

final class YerdchiCanonicalizer {
    func canonicalize(_ url: URL) -> URL? {
        guard var components = URLComponents(url: url, resolvingAgainstBaseURL: true) else {
            return nil
        }

        components.fragment = nil
        components.scheme = components.scheme?.lowercased()
        components.host = components.host?.lowercased()

        if components.scheme == "http", components.port == 80 {
            components.port = nil
        } else if components.scheme == "https", components.port == 443 {
            components.port = nil
        }

        let trackingPrefixes = ["utm_", "pk_", "mc_"]
        let trackingKeys: Set<String> = ["fbclid", "gclid", "dclid", "msclkid"]
        components.queryItems = components.queryItems?
            .filter { item in
                let key = item.name.lowercased()
                return !trackingKeys.contains(key) && !trackingPrefixes.contains(where: key.hasPrefix)
            }
            .sorted { lhs, rhs in
                if lhs.name == rhs.name { return (lhs.value ?? "") < (rhs.value ?? "") }
                return lhs.name < rhs.name
            }

        if components.path.isEmpty {
            components.path = "/"
        } else if components.path.count > 1, components.path.hasSuffix("/") {
            components.path.removeLast()
        }

        return components.url
    }
}

final class YerdchiFrontier {
    private var jobs: [String: YerdchiURLJob] = [:]
    private var hostLastDispatch: [String: Date] = [:]
    private var activePerHost: [String: Int] = [:]
    private let lock = NSLock()
    private let canonicalizer = YerdchiCanonicalizer()
    private let configuration: YerdchiConfiguration

    init(configuration: YerdchiConfiguration) {
        self.configuration = configuration
    }

    @discardableResult
    func enqueue(
        _ rawURL: URL,
        depth: Int,
        parentURL: String? = nil,
        semanticPriority: Double = 0
    ) -> Bool {
        guard depth <= configuration.maxDepth,
              let normalized = canonicalizer.canonicalize(rawURL),
              let host = normalized.host,
              normalized.scheme == "http" || normalized.scheme == "https" else {
            return false
        }

        if !configuration.allowedHosts.isEmpty,
           !configuration.allowedHosts.contains(host) {
            return false
        }

        let key = normalized.absoluteString
        lock.lock()
        defer { lock.unlock() }

        guard jobs[key] == nil, jobs.count < configuration.maxPages else {
            return false
        }

        jobs[key] = YerdchiURLJob(
            id: UUID(),
            url: normalized,
            canonicalURL: key,
            host: host,
            depth: depth,
            parentURL: parentURL,
            discoveredAt: Date(),
            nextEligibleAt: Date(),
            leaseExpiresAt: nil,
            attempts: 0,
            priority: semanticPriority - Double(depth) * 0.05,
            state: .queued,
            lastError: nil
        )
        return true
    }

    func leaseNext(now: Date = Date()) -> YerdchiURLJob? {
        lock.lock()
        defer { lock.unlock() }

        reclaimExpiredLeases(now: now)

        let eligible = jobs.values
            .filter { job in
                guard job.state == .queued, job.nextEligibleAt <= now else { return false }
                let active = activePerHost[job.host, default: 0]
                guard active < configuration.perHostConcurrency else { return false }
                if let last = hostLastDispatch[job.host],
                   now.timeIntervalSince(last) < configuration.minimumHostDelay {
                    return false
                }
                return true
            }
            .sorted { lhs, rhs in
                if lhs.priority == rhs.priority {
                    return lhs.discoveredAt < rhs.discoveredAt
                }
                return lhs.priority > rhs.priority
            }

        guard var selected = eligible.first else { return nil }
        selected.state = .leased
        selected.attempts += 1
        selected.leaseExpiresAt = now.addingTimeInterval(configuration.leaseDuration)
        jobs[selected.canonicalURL] = selected
        hostLastDispatch[selected.host] = now
        activePerHost[selected.host, default: 0] += 1
        return selected
    }

    func complete(_ job: YerdchiURLJob) {
        transition(job, to: .succeeded, error: nil, retryAt: nil)
    }

    func block(_ job: YerdchiURLJob, reason: String) {
        transition(job, to: .blocked, error: reason, retryAt: nil)
    }

    func fail(_ job: YerdchiURLJob, error: String, now: Date = Date()) {
        let shouldRetry = job.attempts < configuration.maxRetries
        let delay = min(pow(2.0, Double(max(job.attempts - 1, 0))), 60.0)
        transition(
            job,
            to: shouldRetry ? .queued : .failed,
            error: error,
            retryAt: shouldRetry ? now.addingTimeInterval(delay) : nil
        )
    }

    func snapshot() -> [YerdchiURLJob] {
        lock.lock()
        defer { lock.unlock() }
        return jobs.values.sorted { $0.discoveredAt < $1.discoveredAt }
    }

    private func transition(
        _ job: YerdchiURLJob,
        to state: YerdchiJobState,
        error: String?,
        retryAt: Date?
    ) {
        lock.lock()
        defer { lock.unlock() }
        guard var current = jobs[job.canonicalURL] else { return }
        if current.state == .leased {
            activePerHost[current.host] = max(activePerHost[current.host, default: 1] - 1, 0)
        }
        current.state = state
        current.lastError = error
        current.leaseExpiresAt = nil
        if let retryAt { current.nextEligibleAt = retryAt }
        jobs[current.canonicalURL] = current
    }

    private func reclaimExpiredLeases(now: Date) {
        for (key, var job) in jobs where job.state == .leased {
            guard let expiry = job.leaseExpiresAt, expiry <= now else { continue }
            activePerHost[job.host] = max(activePerHost[job.host, default: 1] - 1, 0)
            job.state = .queued
            job.leaseExpiresAt = nil
            job.nextEligibleAt = now
            job.lastError = "lease expired"
            jobs[key] = job
        }
    }
}

final class YerdchiEngine {
    private let configuration: YerdchiConfiguration
    private let frontier: YerdchiFrontier
    private let canonicalizer = YerdchiCanonicalizer()

    init(configuration: YerdchiConfiguration = YerdchiConfiguration()) {
        self.configuration = configuration
        self.frontier = YerdchiFrontier(configuration: configuration)
    }

    func seed(_ urls: [URL]) {
        for url in urls {
            _ = frontier.enqueue(url, depth: 0, semanticPriority: 1)
        }
    }

    /// Executes one crawl lease using Nyx's existing SemanticLocator.
    /// Returning nil means no eligible job is currently available.
    func crawlNext() -> YerdchiObservation? {
        guard let job = frontier.leaseNext() else { return nil }
        let started = Date()
        let locator = SemanticLocator()

        guard locator.navigate(url: job.url.absoluteString) else {
            frontier.fail(job, error: "navigation failed")
            return nil
        }

        locator.buildIndex()
        let matches = configuration.semanticIntent.isEmpty
            ? []
            : locator.find(configuration.semanticIntent, topK: 10)

        let semanticMatches = matches.map {
            YerdchiSemanticMatch(
                rank: $0.rank,
                score: $0.score,
                tag: $0.element.tag,
                text: String($0.element.text.prefix(500)),
                xpath: $0.element.xpath
            )
        }

        let links = extractLinks(from: locator)
        for link in links {
            guard let url = URL(string: link),
                  let canonical = canonicalizer.canonicalize(url) else { continue }
            let priority = semanticLinkPriority(canonical.absoluteString)
            _ = frontier.enqueue(
                canonical,
                depth: job.depth + 1,
                parentURL: job.canonicalURL,
                semanticPriority: priority
            )
        }

        let title = locator.title()
        let semanticMaterial = semanticMatches
            .map { "\($0.tag)|\($0.text)|\($0.score)" }
            .joined(separator: "\n")

        let observation = YerdchiObservation(
            url: job.canonicalURL,
            title: title,
            contentHash: stableHash(title + links.joined(separator: "\n")),
            semanticHash: stableHash(semanticMaterial),
            discoveredLinks: links,
            semanticMatches: semanticMatches,
            observedAt: Date(),
            elapsedMilliseconds: Int(Date().timeIntervalSince(started) * 1_000)
        )

        frontier.complete(job)
        return observation
    }

    func state() -> [YerdchiURLJob] {
        frontier.snapshot()
    }

    private func semanticLinkPriority(_ url: String) -> Double {
        guard !configuration.semanticIntent.isEmpty else { return 0 }
        let queryTokens = tokenSet(configuration.semanticIntent)
        let urlTokens = tokenSet(url.replacingOccurrences(of: "/", with: " "))
        guard !queryTokens.isEmpty else { return 0 }
        let overlap = queryTokens.intersection(urlTokens).count
        return Double(overlap) / Double(queryTokens.count)
    }

    private func tokenSet(_ value: String) -> Set<String> {
        Set(value.lowercased()
            .components(separatedBy: CharacterSet.alphanumerics.inverted)
            .filter { $0.count > 1 })
    }

    private func stableHash(_ value: String) -> String {
        // FNV-1a 64-bit: deterministic, fast, and dependency-free.
        var hash: UInt64 = 14_695_981_039_346_656_037
        for byte in value.utf8 {
            hash ^= UInt64(byte)
            hash &*= 1_099_511_628_211
        }
        return String(format: "%016llx", hash)
    }

    private func extractLinks(from locator: SemanticLocator) -> [String] {
        // Nyx already indexes anchor elements. Querying for links avoids exposing
        // WebKit internals and keeps discovery coupled to the semantic layer.
        let candidates = locator.find("link navigation destination", topK: 500)
        var seen = Set<String>()
        var output: [String] = []

        for match in candidates {
            guard let raw = match.element.attrs["href"],
                  let base = URL(string: locator.currentURL()),
                  let resolved = URL(string: raw, relativeTo: base)?.absoluteURL,
                  let canonical = canonicalizer.canonicalize(resolved) else { continue }
            let value = canonical.absoluteString
            if seen.insert(value).inserted { output.append(value) }
        }
        return output
    }
}
