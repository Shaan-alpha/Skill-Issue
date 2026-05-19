# Bundled fonts

Inter (`Inter-Medium.ttf`, `Inter-Bold.ttf`) by Rasmus Andersson, licensed
under the SIL Open Font License 1.1.

Source: https://github.com/rsms/inter (release v4.0).

Bundled here because `next/og`'s `ImageResponse` reads font binaries on
every render; fetching them remotely on each cold start would add latency.
