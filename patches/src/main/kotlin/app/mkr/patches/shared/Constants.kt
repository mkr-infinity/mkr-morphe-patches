// Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
// Shared compatibility definitions and constants for custom patches.

package app.mkr.patches.shared

import app.morphe.patcher.patch.ApkFileType
import app.morphe.patcher.patch.AppTarget
import app.morphe.patcher.patch.Compatibility

object Constants {
    // Smart Launcher (ginlemon.flowerfree)
    val COMPATIBILITY_SMART_LAUNCHER = Compatibility(
        name = "Smart Launcher",
        packageName = "ginlemon.flowerfree",
        apkFileType = ApkFileType.APK,
        appIconColor = 0x2196F3,
        targets = listOf(
            AppTarget(
                version = "6.4 build 049",
                isExperimental = true
            ),
            AppTarget(
                version = "6.4 build 048",
                isExperimental = true
            ),
            AppTarget(
                version = "6.4",
                isExperimental = true
            )
        )
    )

    // MovieBox (com.movieboxpro.android / com.community.mbox.tv)
    val COMPATIBILITY_MOVIEBOX = Compatibility(
        name = "MovieBox",
        packageName = "com.movieboxpro.android",
        apkFileType = ApkFileType.APK,
        appIconColor = 0xFF5722,
        targets = listOf(
            AppTarget(
                version = "15.7",
                isExperimental = true
            ),
            AppTarget(
                version = "15.6",
                isExperimental = false
            ),
            AppTarget(
                version = "15.5",
                isExperimental = false
            )
        )
    )

    // Telegram (org.telegram.messenger)
    val COMPATIBILITY_TELEGRAM = Compatibility(
        name = "Telegram",
        packageName = "org.telegram.messenger",
        apkFileType = ApkFileType.APK,
        appIconColor = 0x24A1DE,
        targets = listOf(
            AppTarget(
                version = "11.8.2",
                isExperimental = false
            ),
            AppTarget(
                version = "11.7.1",
                isExperimental = false
            )
        )
    )

    // Twitch (tv.twitch.android.app)
    val COMPATIBILITY_TWITCH = Compatibility(
        name = "Twitch",
        packageName = "tv.twitch.android.app",
        apkFileType = ApkFileType.APK,
        appIconColor = 0x9146FF,
        targets = listOf(
            AppTarget(version = "20.8.0", isExperimental = true),
            AppTarget(version = "20.7.0", isExperimental = false)
        )
    )

    // Duolingo (com.duolingo)
    val COMPATIBILITY_DUOLINGO = Compatibility(
        name = "Duolingo",
        packageName = "com.duolingo",
        apkFileType = ApkFileType.APK,
        appIconColor = 0x58CC02,
        targets = listOf(
            AppTarget(version = "6.28.2", isExperimental = true),
            AppTarget(version = "6.25.4", isExperimental = false)
        )
    )

    // Messenger (com.facebook.orca)
    val COMPATIBILITY_MESSENGER = Compatibility(
        name = "Messenger",
        packageName = "com.facebook.orca",
        apkFileType = ApkFileType.APK,
        appIconColor = 0x0084FF,
        targets = listOf(
            AppTarget(version = "480.0.0.45.109", isExperimental = true),
            AppTarget(version = "475.0.0.40.108", isExperimental = false)
        )
    )

    // Discord (com.discord)
    val COMPATIBILITY_DISCORD = Compatibility(
        name = "Discord",
        packageName = "com.discord",
        apkFileType = ApkFileType.APK,
        appIconColor = 0x5865F2,
        targets = listOf(
            AppTarget(version = "250.0", isExperimental = true),
            AppTarget(version = "248.0", isExperimental = false)
        )
    )

    // Example generic hook
    val COMPATIBILITY_EXAMPLE = Compatibility(
        name = "MKR Custom Target",
        packageName = "com.mkr.custom.app",
        apkFileType = ApkFileType.APK,
        appIconColor = 0xFF9800,
        targets = listOf(
            AppTarget(version = "1.0.0")
        )
    )
}

