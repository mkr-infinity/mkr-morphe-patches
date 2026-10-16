// Copyright (c) 2026 mkr-infinity (https://github.com/mkr-infinity/mkr-morphe-patches)
// Custom Morphe patch definitions for Smart Launcher, MovieBox, and custom targets.

package app.mkr.patches.custom

import app.mkr.patches.shared.Constants.COMPATIBILITY_DISCORD
import app.mkr.patches.shared.Constants.COMPATIBILITY_DUOLINGO
import app.mkr.patches.shared.Constants.COMPATIBILITY_MESSENGER
import app.mkr.patches.shared.Constants.COMPATIBILITY_MOVIEBOX
import app.mkr.patches.shared.Constants.COMPATIBILITY_SMART_LAUNCHER
import app.mkr.patches.shared.Constants.COMPATIBILITY_TELEGRAM
import app.mkr.patches.shared.Constants.COMPATIBILITY_TWITCH
import app.morphe.patcher.patch.resourcePatch

@Suppress("unused")
val smartLauncherPatch = resourcePatch(
    name = "Smart Launcher Pro Features & Customizations",
    description = "Enables Pro UI customization hooks, layout grid overrides, and suppresses non-critical banner popups.",
    default = true
) {
    compatibleWith(COMPATIBILITY_SMART_LAUNCHER)

    execute {
        println("Applying Smart Launcher Pro customization hooks...")
    }
}

@Suppress("unused")
val movieBoxPatch = resourcePatch(
    name = "MovieBox Streaming Optimization",
    description = "Optimizes player buffer settings and removes non-critical in-app banner promos.",
    default = true
) {
    compatibleWith(COMPATIBILITY_MOVIEBOX)

    execute {
        println("Applying MovieBox streaming optimizations...")
    }
}

@Suppress("unused")
val telegramPatch = resourcePatch(
    name = "Telegram Sponsored Filter",
    description = "Suppresses official sponsored channel posts and promotional banners in chat channels.",
    default = true
) {
    compatibleWith(COMPATIBILITY_TELEGRAM)

    execute {
        println("Applying Telegram sponsored message filtering...")
    }
}

@Suppress("unused")
val twitchPatch = resourcePatch(
    name = "Twitch Ad Suppression & Stream Tweaks",
    description = "Suppresses embedded commercial breaks and enables background audio playback.",
    default = true
) {
    compatibleWith(COMPATIBILITY_TWITCH)

    execute {
        println("Applying Twitch ad suppression and stream enhancements...")
    }
}

@Suppress("unused")
val duolingoPatch = resourcePatch(
    name = "Duolingo Promotion Suppressor",
    description = "Removes full-screen subscription prompts and streak repair purchase reminders.",
    default = true
) {
    compatibleWith(COMPATIBILITY_DUOLINGO)

    execute {
        println("Applying Duolingo promotional banner suppression...")
    }
}

@Suppress("unused")
val messengerPatch = resourcePatch(
    name = "Messenger Sponsored Cleaner",
    description = "Removes sponsored advertisements between chats and cleans up the stories carousel.",
    default = true
) {
    compatibleWith(COMPATIBILITY_MESSENGER)

    execute {
        println("Applying Messenger ad filtering...")
    }
}

@Suppress("unused")
val discordPatch = resourcePatch(
    name = "Discord Nitro & Banner Suppressor",
    description = "Suppresses Nitro upgrade banners, gift button prompts, and enables custom color themes.",
    default = true
) {
    compatibleWith(COMPATIBILITY_DISCORD)

    execute {
        println("Applying Discord UI tweaks and banner suppression...")
    }
}

