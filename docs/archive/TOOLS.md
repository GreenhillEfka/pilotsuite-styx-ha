# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Sonos

(Stand 2026-02-07, aus HA Screenshot)
- Badbereich → Play:1 (Toilette)
- Buerobereich → Port (Arbeitszimmer)
- Gangbereich → One (Gang)
- Kochbereich → Play:1 (Küche)
- Schlafbereich → Play:3 (Schlafzimmer)
- Sonos Move! → Move (Kontrollraum)
- Wohnbereich → Connect (Wohnzimmer)

Entity-IDs:
- Badbereich → `media_player.badbereich`
- Buerobereich → `media_player.buerobereich`
- Gangbereich → `media_player.gangbereich`
- Kochbereich → `media_player.kochbereich`
- Schlafbereich → `media_player.schlafbereich`
- Sonos Move! → `media_player.sonos_move`
- Wohnbereich → `media_player.wohnbereich`

## Spotify
- Player Entity: `media_player.spotify_efka`

## TV (Wohnzimmer)
- SmartTV: `media_player.fernseher_im_wohnzimmer`
- Apple TV: `media_player.apple_tv_wohnzimmer`

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.
